from django.db import migrations

FUND_ACCOUNTS = [
    {'code': 'CAPITAL',     'name': 'Capital',     'allow_negative': False, 'is_active': True},
    {'code': 'SOCIAL',      'name': 'Social',      'allow_negative': True,  'is_active': True},
    {'code': 'SOCIAL_PLUS', 'name': 'Social Plus', 'allow_negative': True,  'is_active': True},
]


def seed_fund_accounts(apps, schema_editor):
    FundAccount = apps.get_model('core', 'FundAccount')
    for data in FUND_ACCOUNTS:
        FundAccount.objects.get_or_create(code=data['code'], defaults=data)


def reverse_fund_accounts(apps, schema_editor):
    FundAccount = apps.get_model('core', 'FundAccount')
    FundAccount.objects.filter(code__in=[d['code'] for d in FUND_ACCOUNTS]).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0003_fundaccount'),
    ]

    operations = [
        migrations.RunPython(seed_fund_accounts, reverse_code=reverse_fund_accounts),
    ]
