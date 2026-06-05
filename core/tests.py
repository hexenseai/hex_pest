import datetime
from unittest.mock import patch
from django.test import TestCase
from django.core import mail
from django.contrib.admin.sites import AdminSite
from core.models import Customer, Facility, BagimsizTespit
from addressbook.models import ContactCategory, Contact
from core.emails import send_bagimsiz_tespit_email
from core.admin import BagimsizTespitAdmin

class FakeRequest:
    def __init__(self, user=None):
        self.user = user

class BagimsizTespitEmailTestCase(TestCase):
    def setUp(self):
        # 1. Create a customer
        self.customer = Customer.objects.create(
            kod="TESTCUST",
            firma_ismi="Test Firması A.Ş."
        )
        
        # 2. Create a contact category
        self.category = ContactCategory.objects.create(
            ad="Yetkili",
            sira=1
        )
        
        # 3. Create contacts (one with email, one without)
        self.contact1 = Contact.objects.create(
            category=self.category,
            customer=self.customer,
            ad_soyad="Ahmet Yılmaz",
            email="ahmet@example.com"
        )
        self.contact2 = Contact.objects.create(
            category=self.category,
            customer=self.customer,
            ad_soyad="Mehmet Can",
            email=""
        )
        
        # 4. Create an independent detection record (BagimsizTespit)
        self.tespit = BagimsizTespit(
            tarih=datetime.date.today(),
            firma=self.customer,
            yer_aciklamasi="Giriş Kapısı",
            gozlem_aciklamasi="Açık bırakılmış",
            oneriler="Kapatılmalı"
        )
        # Note: we don't call save() yet because we want to test both manually sending
        # and saving via admin.

    def test_send_email_success(self):
        # Save detection
        self.tespit.save()
        
        # Clear outbox
        mail.outbox = []
        
        # Send email
        result = send_bagimsiz_tespit_email(self.tespit)
        
        # Check result
        self.assertTrue(result)
        self.assertEqual(len(mail.outbox), 1)
        email = mail.outbox[0]
        
        # Check recipients and content
        self.assertIn("ahmet@example.com", email.to)
        self.assertNotIn("mehmet@example.com", email.to)
        self.assertIn("Test Firması A.Ş.", email.body)
        self.assertIn("Giriş Kapısı", email.body)
        self.assertIn("Açık bırakılmış", email.body)
        self.assertIn("Kapatılmalı", email.body)

    def test_send_email_no_contacts(self):
        # Remove contacts
        Contact.objects.all().delete()
        self.tespit.save()
        
        # Clear outbox
        mail.outbox = []
        
        # Send email
        result = send_bagimsiz_tespit_email(self.tespit)
        
        # Should return False and not send any email
        self.assertFalse(result)
        self.assertEqual(len(mail.outbox), 0)

    @patch('django.contrib.messages.add_message')
    def test_admin_save_model_triggers_email(self, mock_add_message):
        # Clear outbox
        mail.outbox = []
        
        # Instantiate admin class
        site = AdminSite()
        admin_instance = BagimsizTespitAdmin(BagimsizTespit, site)
        
        # Trigger save_model (which should call send_bagimsiz_tespit_email internally)
        request = FakeRequest()
        admin_instance.save_model(request, self.tespit, form=None, change=False)
        
        # Verify it was saved to DB
        self.assertIsNotNone(self.tespit.pk)
        
        # Verify email was sent (console backend or test backend writes to outbox)
        self.assertEqual(len(mail.outbox), 1)
        email = mail.outbox[0]
        self.assertIn("ahmet@example.com", email.to)
        
        # Verify messages was called
        mock_add_message.assert_called_once()

    def test_admin_save_model_no_trigger_on_change(self):
        # Save first
        self.tespit.save()
        
        # Clear outbox
        mail.outbox = []
        
        # Instantiate admin class
        site = AdminSite()
        admin_instance = BagimsizTespitAdmin(BagimsizTespit, site)
        
        # Update something and trigger save_model with change=True
        self.tespit.yer_aciklamasi = "Arka Kapı"
        request = FakeRequest()
        admin_instance.save_model(request, self.tespit, form=None, change=True)
        
        # Verify no email is triggered on modification
        self.assertEqual(len(mail.outbox), 0)
