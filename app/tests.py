from django.test import TestCase

from django.contrib.auth.models import User, Group
from django.contrib import messages
from django.test import Client

from .models import Project, Task
from .boot import boot

import api.tests

class TestApp(TestCase):

    fixtures = ['test_users', 'test_processingnodes', ]

    @classmethod
    def setUpClass(cls):
        super(TestApp, cls).setUpClass()
        boot()

    def setUp(self):
        self.credentials = {
            'username': 'testuser',
            'password': 'test1234',
            'email': 'test@mail.com'}

        # Create a test Group
        my_group, created = Group.objects.get_or_create(name='test_group')

        # Add user to test Group
        User.objects.get(pk=1).groups.add(my_group)

    def tearDown(self):
        pass

    def test_user_login(self):
        c = Client()
        # User points the browser to the landing page
        res = c.post('/', follow=True)

        # the user is not logged in
        self.assertFalse(res.context['user'].is_authenticated)
        # and is redirected to the login page
        self.assertRedirects(res, '/login/')

        # The login page is being rendered by the correct template
        self.assertTemplateUsed(res, 'registration/login.html')

        # asks the user to login using a set of valid credentials
        res = c.post('/login/', data=self.credentials, follow=True)

        # The system acknowledges him
        self.assertTrue(res.context['user'].is_authenticated)

        # and moves him at the dashboard
        self.assertTemplateUsed(res, 'app/dashboard.html')

    def test_views(self):
        c = Client()

        # Connecting to dashboard without auth redirects to /
        res = c.get('/dashboard/', follow=True)
        self.assertFalse(res.context['user'].is_authenticated)
        self.assertRedirects(res, '/login/?next=/dashboard/')

        res = c.get('/processingnode/1/', follow=True)
        self.assertRedirects(res, '/login/?next=/processingnode/1/')

        # Login
        c.post('/login/', data=self.credentials, follow=True)

        # We should have a project created from the dashboard
        self.assertTrue(Project.objects.count() >= 1)

        # We can access a processingnode view that exists
        res = c.get('/processingnode/1/')
        self.assertTrue(res.status_code == 200)
        self.assertTemplateUsed(res, 'app/processing_node.html')

        # We can access a processingnode that is offline
        # (and there's a warning message when we do that)
        res = c.get('/processingnode/2/')
        self.assertTrue(res.status_code == 200)
        self.assertTemplateUsed(res, 'app/processing_node.html')

        message = list(res.context['messages'])[0]
        self.assertEqual(message.tags, 'warning')
        self.assertTrue("offline" in message.message)

        res = c.get('/processingnode/9999/')
        self.assertTrue(res.status_code == 404)

        res = c.get('/processingnode/abc/')
        self.assertTrue(res.status_code == 404)

    def test_default_group(self):
        # It exists
        self.assertTrue(Group.objects.filter(name='Default').count() == 1)

        # Verify that all new users are assigned to default group
        u = User.objects.create_user(username="default_user")
        u.refresh_from_db()
        self.assertTrue(u.groups.filter(name='Default').count() == 1)

    def test_projects(self):
        # Get a normal user
        user = User.objects.get(pk=2)
        self.assertFalse(user.is_superuser)

        # Create a new project
        p = Project(owner=user, name="test")
        p.save()

        # Have the proper permissions been set?
        self.assertTrue(user.has_perm("view_project", p))
        self.assertTrue(user.has_perm("add_project", p))
        self.assertTrue(user.has_perm("change_project", p))
        self.assertTrue(user.has_perm("delete_project", p))

        # Get a superuser
        superUser = User.objects.get(pk=1)
        self.assertTrue(superUser.is_superuser)

        # He should also have permissions, although not explicitly set
        self.assertTrue(superUser.has_perm("delete_project", p))

        # Get another user
        anotherUser = User.objects.get(pk=3)
        self.assertFalse(anotherUser.is_superuser)

        # Should not have permission
        self.assertFalse(anotherUser.has_perm("delete_project", p))
