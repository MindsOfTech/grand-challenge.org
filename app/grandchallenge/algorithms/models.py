import logging
from pathlib import Path
from tempfile import TemporaryDirectory

from django.conf import settings
from django.contrib.auth.models import Group
from django.core.exceptions import ObjectDoesNotExist
from django.db import models
from django.db.models.signals import post_delete
from django.dispatch import receiver
from django.utils._os import safe_join
from django_extensions.db.models import TitleSlugDescriptionModel
from guardian.shortcuts import assign_perm, get_objects_for_group, remove_perm

from grandchallenge.cases.image_builders.metaio_mhd_mha import (
    image_builder_mhd,
)
from grandchallenge.cases.image_builders.tiff import image_builder_tiff
from grandchallenge.cases.tasks import import_images
from grandchallenge.challenges.models import get_logo_path
from grandchallenge.components.backends.docker import (
    Executor,
    cleanup,
    get_file,
)
from grandchallenge.components.models import (
    ComponentImage,
    ComponentInterface,
    ComponentInterfaceValue,
    ComponentJob,
)
from grandchallenge.core.models import RequestBase, UUIDModel
from grandchallenge.core.storage import public_s3_storage
from grandchallenge.subdomains.utils import reverse
from grandchallenge.workstations.models import Workstation

logger = logging.getLogger(__name__)

DEFAULT_INPUT_INTERFACE_SLUG = "generic-medical-image"
DEFAULT_OUTPUT_INTERFACE_SLUG = "generic-overlay"


class Algorithm(UUIDModel, TitleSlugDescriptionModel):
    editors_group = models.OneToOneField(
        Group,
        on_delete=models.CASCADE,
        editable=False,
        related_name="editors_of_algorithm",
    )
    users_group = models.OneToOneField(
        Group,
        on_delete=models.CASCADE,
        editable=False,
        related_name="users_of_algorithm",
    )
    logo = models.ImageField(
        upload_to=get_logo_path, storage=public_s3_storage
    )
    workstation = models.ForeignKey(
        "workstations.Workstation", on_delete=models.CASCADE
    )
    workstation_config = models.ForeignKey(
        "workstation_configs.WorkstationConfig",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )
    public = models.BooleanField(
        default=False,
        help_text=(
            "Should this algorithm be visible to all users on the algorithm "
            "overview page? This does not grant all users permission to use "
            "this algorithm. Users will still need to be added to the "
            "algorithm users group in order to do that."
        ),
    )
    detail_page_markdown = models.TextField(blank=True)
    job_create_page_markdown = models.TextField(blank=True)
    additional_terms_markdown = models.TextField(
        blank=True,
        help_text=(
            "By using this algortihm, users agree to the site wide "
            "terms of service. If your algorithm has any additional "
            "terms of usage, define them here."
        ),
    )

    inputs = models.ManyToManyField(
        to=ComponentInterface, related_name="algorithm_inputs"
    )
    outputs = models.ManyToManyField(
        to=ComponentInterface, related_name="algorithm_outputs"
    )

    class Meta(UUIDModel.Meta, TitleSlugDescriptionModel.Meta):
        ordering = ("created",)
        permissions = [("execute_algorithm", "Can execute algorithm")]

    def __str__(self):
        return f"{self.title}"

    def get_absolute_url(self):
        return reverse("algorithms:detail", kwargs={"slug": self.slug})

    @property
    def api_url(self):
        return reverse("api:algorithm-detail", kwargs={"pk": self.pk})

    def save(self, *args, **kwargs):
        adding = self._state.adding

        if adding:
            self.create_groups()
            self.workstation_id = (
                self.workstation_id or self.default_workstation.pk
            )

        super().save(*args, **kwargs)

        if adding:
            self.set_default_interfaces()

        self.assign_permissions()
        self.assign_workstation_permissions()

    def create_groups(self):
        self.editors_group = Group.objects.create(
            name=f"{self._meta.app_label}_{self._meta.model_name}_{self.pk}_editors"
        )
        self.users_group = Group.objects.create(
            name=f"{self._meta.app_label}_{self._meta.model_name}_{self.pk}_users"
        )

    def set_default_interfaces(self):
        self.inputs.set(
            [ComponentInterface.objects.get(slug=DEFAULT_INPUT_INTERFACE_SLUG)]
        )
        self.outputs.set(
            [ComponentInterface.objects.get(slug="results-json-file")]
        )

    def assign_permissions(self):
        # Editors and users can view this algorithm
        assign_perm(f"view_{self._meta.model_name}", self.editors_group, self)
        assign_perm(f"view_{self._meta.model_name}", self.users_group, self)
        # Editors and users can execute this algorithm
        assign_perm(
            f"execute_{self._meta.model_name}", self.editors_group, self
        )
        assign_perm(f"execute_{self._meta.model_name}", self.users_group, self)
        # Editors can change this algorithm
        assign_perm(
            f"change_{self._meta.model_name}", self.editors_group, self
        )

        reg_and_anon = Group.objects.get(
            name=settings.REGISTERED_AND_ANON_USERS_GROUP_NAME
        )

        if self.public:
            assign_perm(f"view_{self._meta.model_name}", reg_and_anon, self)
        else:
            remove_perm(f"view_{self._meta.model_name}", reg_and_anon, self)

    def assign_workstation_permissions(self):
        """Allow the editors and users group to view the workstation."""
        perm = f"view_{Workstation._meta.model_name}"

        for group in [self.users_group, self.editors_group]:
            workstations = get_objects_for_group(
                group=group, perms=perm, klass=Workstation
            )

            if (
                self.workstation not in workstations
            ) or workstations.count() > 1:
                remove_perm(perm=perm, user_or_group=group, obj=workstations)
                assign_perm(
                    perm=perm, user_or_group=group, obj=self.workstation
                )

    @property
    def latest_ready_image(self):
        """
        Returns
        -------
            The most recent container image for this algorithm
        """
        return (
            self.algorithm_container_images.filter(ready=True)
            .order_by("-created")
            .first()
        )

    @property
    def default_workstation(self):
        """
        Returns the default workstation, creating it if it does not already
        exist.
        """
        w, created = Workstation.objects.get_or_create(
            slug=settings.DEFAULT_WORKSTATION_SLUG
        )

        if created:
            w.title = settings.DEFAULT_WORKSTATION_SLUG
            w.save()

        return w

    def is_editor(self, user):
        return user.groups.filter(pk=self.editors_group.pk).exists()

    def add_editor(self, user):
        # using .pk is required here as it is called from a data migration
        return user.groups.add(self.editors_group.pk)

    def remove_editor(self, user):
        return user.groups.remove(self.editors_group)

    def is_user(self, user):
        return user.groups.filter(pk=self.users_group.pk).exists()

    def add_user(self, user):
        return user.groups.add(self.users_group)

    def remove_user(self, user):
        return user.groups.remove(self.users_group)


@receiver(post_delete, sender=Algorithm)
def delete_algorithm_groups_hook(*_, instance: Algorithm, using, **__):
    """
    Deletes the related groups.

    We use a signal rather than overriding delete() to catch usages of
    bulk_delete.
    """
    try:
        instance.editors_group.delete(using=using)
    except ObjectDoesNotExist:
        pass

    try:
        instance.users_group.delete(using=using)
    except ObjectDoesNotExist:
        pass


class AlgorithmImage(UUIDModel, ComponentImage):
    algorithm = models.ForeignKey(
        Algorithm,
        on_delete=models.CASCADE,
        related_name="algorithm_container_images",
    )
    queue_override = models.CharField(max_length=128, blank=True)

    class Meta(UUIDModel.Meta, ComponentImage.Meta):
        ordering = ("created", "creator")

    def get_absolute_url(self):
        return reverse(
            "algorithms:image-detail",
            kwargs={"slug": self.algorithm.slug, "pk": self.pk},
        )

    @property
    def api_url(self):
        return reverse("api:algorithms-image-detail", kwargs={"pk": self.pk})

    def save(self, *args, **kwargs):
        adding = self._state.adding

        super().save(*args, **kwargs)

        if adding:
            self.assign_permissions()

    def assign_permissions(self):
        # Editors and users can view this algorithm image
        assign_perm(
            f"view_{self._meta.model_name}", self.algorithm.editors_group, self
        )
        # Editors can change this algorithm image
        assign_perm(
            f"change_{self._meta.model_name}",
            self.algorithm.editors_group,
            self,
        )


class AlgorithmExecutor(Executor):
    def __init__(self, *args, **kwargs):
        super().__init__(
            *args, results_file=Path("/output/results.json"), **kwargs
        )
        self.output_images_dir = Path("/output/images/")

    def _get_result(self):
        """Read all of the images in /output/ & convert to an UploadSession."""
        with cleanup(
            self._client.containers.run(
                image=self._io_image,
                volumes={
                    self._output_volume: {"bind": "/output/", "mode": "ro"}
                },
                name=f"{self._job_label}-reader",
                detach=True,
                tty=True,
                labels=self._labels,
                **self._run_kwargs,
            )
        ) as reader:
            self._copy_output_files(
                container=reader, base_dir=Path(self.output_images_dir)
            )

        return super()._get_result()

    def _copy_output_files(self, *, container, base_dir: Path):
        found_files = container.exec_run(f"find {base_dir} -type f")

        if found_files.exit_code != 0:
            logger.warning(f"Error listing {base_dir}")
            return

        output_files = [
            base_dir / Path(f)
            for f in found_files.output.decode().splitlines()
        ]

        if not output_files:
            logger.warning("Output directory is empty")
            return

        with TemporaryDirectory() as tmpdir:
            input_files = set()

            for file in output_files:
                tmpfile = Path(safe_join(tmpdir, file.relative_to(base_dir)))
                tmpfile.parent.mkdir(parents=True, exist_ok=True)

                with open(tmpfile, "wb") as outfile:
                    infile = get_file(container=container, src=file)
                    buffer = True
                    while buffer:
                        buffer = infile.read(1024)
                        outfile.write(buffer)

                input_files.add(tmpfile)

            importer_result = import_images(
                files=input_files,
                builders=[image_builder_mhd, image_builder_tiff],
            )

        default_output_interface = ComponentInterface.objects.get(
            slug=DEFAULT_OUTPUT_INTERFACE_SLUG
        )
        job = self._job_class.objects.get(pk=self._job_id)

        for image in importer_result.new_images:
            civ = ComponentInterfaceValue.objects.create(
                interface=default_output_interface, image=image
            )
            job.outputs.add(civ)


class Job(UUIDModel, ComponentJob):
    algorithm_image = models.ForeignKey(
        AlgorithmImage, on_delete=models.CASCADE
    )
    image = models.ForeignKey(
        "cases.Image", null=True, on_delete=models.SET_NULL
    )
    creator = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL
    )
    public = models.BooleanField(
        default=False,
        help_text=(
            "If True, allow anyone to download this result along "
            "with the input image. Otherwise, only the job creator and "
            "algorithm editor(s) will have permission to download and view "
            "this result."
        ),
    )
    comment = models.TextField(blank=True, default="")

    class Meta:
        ordering = ("created",)

    @property
    def container(self):
        return self.algorithm_image

    @property
    def input_files(self):
        return [
            im.file
            for inpt in self.inputs.all()
            for im in inpt.image.files.all()
        ]

    @property
    def executor_cls(self):
        return AlgorithmExecutor

    def create_result(self, *, result: dict):
        interface = ComponentInterface.objects.get(slug="results-json-file")

        try:
            output_civ = self.outputs.get(interface=interface)
            output_civ.value = result
            output_civ.save()
        except ObjectDoesNotExist:
            output_civ = ComponentInterfaceValue.objects.create(
                interface=interface, value=result
            )
            self.outputs.add(output_civ)

    def get_absolute_url(self):
        return reverse("algorithms:jobs-detail", kwargs={"pk": self.pk})

    @property
    def api_url(self):
        return reverse("api:algorithms-job-detail", kwargs={"pk": self.pk})

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

        self.assign_permissions()
        self.assign_public_permissions()
        self.update_interface_image_permissions()

    def assign_permissions(self):
        # Editors and creators can view this job
        assign_perm(
            f"view_{self._meta.model_name}",
            self.algorithm_image.algorithm.editors_group,
            self,
        )

        if self.creator:
            assign_perm(f"view_{self._meta.model_name}", self.creator, self)

        # Algorithm editors can change this job
        assign_perm(
            f"change_{self._meta.model_name}",
            self.algorithm_image.algorithm.editors_group,
            self,
        )

    def assign_public_permissions(self):
        g = Group.objects.get(
            name=settings.REGISTERED_AND_ANON_USERS_GROUP_NAME
        )

        if self.public:
            assign_perm(f"view_{self._meta.model_name}", g, self)
        else:
            remove_perm(f"view_{self._meta.model_name}", g, self)

    def update_interface_image_permissions(self):
        for interface_value in [*self.inputs.all(), *self.outputs.all()]:
            if interface_value.image:
                interface_value.image.update_public_group_permissions()


class AlgorithmPermissionRequest(RequestBase):
    """
    When a user wants to view an algorithm, editors have the option of
    reviewing each user before accepting or rejecting them. This class records
    the needed info for that.
    """

    algorithm = models.ForeignKey(
        Algorithm,
        help_text="To which algorithm has the user requested access?",
        on_delete=models.CASCADE,
    )
    rejection_text = models.TextField(
        blank=True,
        help_text=(
            "The text that will be sent to the user with the reason for their "
            "rejection."
        ),
    )

    @property
    def base_object(self):
        return self.algorithm

    @property
    def object_name(self):
        return self.base_object.title

    @property
    def add_method(self):
        return self.base_object.add_user

    @property
    def remove_method(self):
        return self.base_object.remove_user

    @property
    def permission_list_url(self):
        return reverse(
            "algorithms:permission-request-list",
            kwargs={"slug": self.base_object.slug},
        )

    def __str__(self):
        return f"{self.object_name} registration request by user {self.user.username}"

    class Meta(RequestBase.Meta):
        unique_together = (("algorithm", "user"),)
