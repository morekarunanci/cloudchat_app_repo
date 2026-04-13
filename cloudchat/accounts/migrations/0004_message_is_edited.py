from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0003_message'),
    ]

    operations = [
        migrations.AddField(
            model_name='message',
            name='is_edited',
            field=models.BooleanField(default=False),
        ),
    ]
