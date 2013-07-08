"""
This contains tests using the unittest module. These will pass
when you run "manage.py test.


"""
import pdb
import re

from django.test import TestCase
from django.test.client import RequestFactory
from django.test.utils import override_settings
from django.core.urlresolvers import reverse
from django.core import mail
from django.contrib import admin
from django.contrib.auth.models import User


from comicmodels.models import Page,ComicSite
from comicsite.admin import ComicSiteAdmin,PageAdmin
from profiles.admin import UserProfileAdmin
from profiles.models import UserProfile
from profiles.forms import SignupFormExtra



def get_or_create_user(username,password):
    query_result = User.objects.filter(username=username)
    if query_result.exists():
        return query_result[0]
        
    else:
        return 
    
        
        


def create_comicsite_in_admin(user,short_name,description="test project"):
    """ Create a ComicSite object as if created through django admin interface.
    
    """
    site = ComicSite.objects.create(short_name=short_name,
                             description=description)
    site.save()
    
    # because we are creating a ComicSite directly, some methods from admin
    # are not being called as they should. Do this manually
    ad = ComicSiteAdmin(ComicSite,admin.site)        
    url = reverse("admin:comicmodels_comicsite_add")                
    factory = RequestFactory()
    request = factory.get(url)
    request.user = user            
    ad.set_base_permissions(request,site)
    
    return site
    

                  
def create_page_in_admin(comicsite,title,content="testcontent"):
    """ Create a Page object as if created through django admin interface.
    
    """
    page_admin = PageAdmin(Page,admin.site)
    page = Page.objects.create(title=title,
                               comicsite=comicsite,
                               html=content,
                               permission_lvl=Page.ALL)
    page_admin.first_save(page)
    return page
    
        

class SimpleTest(TestCase):
    def test_basic_addition(self):
        """ Tests that 1 + 1 always equals 2.
        
        """
        self.assertEqual(1 + 1, 2)


class ViewsTest(TestCase):
    
    @override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.'
                                     'EmailBackend')
    
    #use fast, non-safe password hashing to speed up testing
    @override_settings(PASSWORD_HASHERS=('django.contrib.auth.hashers.'
                                        'SHA1PasswordHasher',))
    
    def setUp(self):
        """ Create some objects to work with, In part this is done through
        admin views, meaning admin views are also tested here.
        """
        # Create three types of users that exist: Root, can do anything, 
        # Siteadmin, cam do things to a site he or she owns. And logged in
        # user 
        
        root = User.objects.create_user('root',
                                        'w.s.kerkstra@gmail.com',
                                        'rootpassword')        
        root.is_staff = True
        root.is_superUser = True
        root.save()
        
        # non-root users are created as if they signed up through the site,
        # to maximize test coverage.        
        user1 = self._create_user({"username":"user1"})
                        
        siteadmin = User.objects.create_user('siteadmin1',
                                        'w.s.kerkstra@gmail.com',
                                        'password1')
                
        siteadmin.is_staff = True        
        siteadmin.save()
                    
        testsite = create_comicsite_in_admin(root,"viewtest")                
        create_page_in_admin(testsite,"testpage1")
        create_page_in_admin(testsite,"testpage2")
        
        
    def _signup_user(self,overwrite_data={}):
        """ Create a user in the same way as a new user is signed up on the site.
        any key specified in data overwrites default key passed to form.
        For example, signup_user({'username':'user1'}) to creates a user called 
        'user1' and fills the rest with default data.  
        
        
        """    
        data = {'first_name':'test',
                'last_name':'test',
                'username':'test',            
                'email':'test@test.com',
                'password1':'test',
                'password2':'test',
                'institution':'test',
                'department':'test', 
                'country':'NL',
                'website':'testwebsite',
                'comicsite':'testcomicwebsite'}
        
        data.update(overwrite_data) #overwrite any key in default if in data
        
        
        signin_page = self.client.post(reverse("userena.views.signup"),data)
                
        # check whether signin succeeded. If succeeded the response will be a
        # httpResponseRedirect object, which has a 'Location' key in its
        # items(). Don't know how to better check for type here.
        list = [x[0] for x in signin_page.items()]
        
        self.assertTrue('Location' in list, "could not create user. dumping"
                        " page:\n %s"
                        % signin_page.content)
        

    def _create_user(self,data):
        """ Sign up user in a way as close to production as possible. Check a 
        lot of stuff
        
        """        
        
        self._signup_user(data)
        
        
        validation_mail = mail.outbox[-1]        
        self.assertTrue("signup" in validation_mail.subject,"There was no email"
                        " sent which had 'signup' in the subject line")
        
                    
        self.assertEqual(self.client.get('/accounts/user1/').status_code,403,
                         "Could access user account without using validation" 
                         "link!")
        
        # validate the user with the link that was emailed
        validationlink_result = re.search('/example.com(.*)\n',
                                          validation_mail.body,
                                          re.IGNORECASE)
        
        self.assertTrue(validationlink_result, "could not find any link in" 
                        "registration email")
        
        validationlink = validationlink_result.group(1)        
        response = self.client.get(validationlink)
        
        self.assertEqual(self.client.get('/accounts/user1/').status_code,200,
                         "Could not access user account after using validation" 
                         "link!")
            
        welcome_mail = mail.outbox[-1]
        #TODO check welcome mail
        
        
        query_result = User.objects.filter(username=data['username'])        
        return query_result[0] 
        


    def _login_as_root_user(self):
        """ log in comicmodels.tests.ViewsTest object testcase as admin. Assert 
        whether login was successful. Convenience function to save a few lines of 
        code.  
    
        """        
        success = self.client.login(username='root',password='rootpassword')    
        return success

    
    def _test_as_root(self,url):
        """ Log in as root and try to load url, will assert whether this works 
        
        """   
                         
        self._login_as_root_user()            
        response = self.client.get(url)                        
        self.assertEqual(response.status_code, 200, "loading %s as root "
                        "failed, full response was %s" % (url,response.content))
                        
    
    
        
    def test_page_permissions_view(self):
        """ Test that the permissions page does not crash:
        https://github.com/comic/comic-django/issues/180 
        
        """
        
        testpage1 = Page.objects.filter(title='testpage1')
        self.assert_(testpage1.exists(),"could not find page 'testpage1'")                 
        url = reverse("admin:comicmodels_page_permissions",
                      args=[testpage1[0].pk])
        self._test_as_root(url)
    
    def test_page_change_view(self):
        """ Root can see a page 
        
        """        
        testpage1 = Page.objects.filter(title='testpage1')
        self.assert_(testpage1.exists(),"could not find page 'testpage1'")                 
        url = reverse("admin:comicmodels_page_change",
                      args=[testpage1[0].pk])
        self._test_as_root(url)
