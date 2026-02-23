# Generated migration for passenger status fix

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('bookings', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='passenger',
            name='status',
            field=models.CharField(
                choices=[
                    ('PENDING', 'Pending'),
                    ('CONFIRMED', 'Confirmed'),
                    ('CANCELLED', 'Cancelled'),
                    ('EXPIRED', 'Expired')
                ],
                default='PENDING',
                max_length=20
            ),
        ),
    ]
