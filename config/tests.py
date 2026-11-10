from unittest.mock import patch

from django.db import OperationalError
from django.test import TestCase


class HealthTests(TestCase):
    def test_healthy_database(self):
        response = self.client.get('/healthz/')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {'status': 'ok'})

    @patch('config.urls.connection.cursor', side_effect=OperationalError('private details'))
    def test_unreachable_database(self, mock_cursor):
        response = self.client.get('/healthz/')

        mock_cursor.assert_called_once()
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json(), {'status': 'unavailable'})
