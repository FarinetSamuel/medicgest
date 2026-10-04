import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('prescriptions', '0003_resynchronise_quantite_prises_attendues'),
    ]

    operations = [
        migrations.AddField(
            model_name='horaireprogramme',
            name='intervalle_jours',
            field=models.PositiveSmallIntegerField(
                default=1,
                help_text='Nombre de jours entre deux prises à cet horaire : 1 = tous les jours, 2 = tous les 2 jours, 7 = toutes les semaines, 14 = toutes les 2 semaines.',
                validators=[
                    django.core.validators.MinValueValidator(1),
                    django.core.validators.MaxValueValidator(365),
                ],
            ),
        ),
        migrations.AddField(
            model_name='horaireprogramme',
            name='date_reference',
            field=models.DateField(
                blank=True,
                help_text='Jour de la première prise à cet horaire ; les suivantes en sont déduites par pas de intervalle_jours. Vide = date de début de la prescription.',
                null=True,
            ),
        ),
    ]
