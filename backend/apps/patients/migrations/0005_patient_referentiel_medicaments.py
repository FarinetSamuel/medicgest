from django.db import migrations, models


def deduire_referentiel_existant(apps, schema_editor):
    """
    Avant ce champ, le pays était un filtre d'affichage côté frontend. Un
    patient dont TOUTES les prescriptions et boîtes viennent de Swissmedic
    passe en SWISSMEDIC ; tous les autres restent en BDPM (défaut). Un
    patient déjà mélangé n'est pas deviné : il reste en BDPM et son cas
    doit être traité manuellement.
    """
    Patient = apps.get_model("patients", "Patient")
    Prescription = apps.get_model("prescriptions", "Prescription")
    Boite = apps.get_model("stock", "Boite")

    sources = {}
    for modele in (Prescription, Boite):
        for patient_id, source in modele.objects.values_list("patient_id", "medicament__source").distinct():
            sources.setdefault(patient_id, set()).add(source)

    ids_suisses = [pid for pid, s in sources.items() if s == {"SWISSMEDIC"}]
    Patient.objects.filter(pk__in=ids_suisses).update(referentiel_medicaments="SWISSMEDIC")


class Migration(migrations.Migration):

    dependencies = [
        ("patients", "0004_patient_preference_alerte_stock"),
        ("prescriptions", "0001_initial"),
        ("stock", "0001_initial"),
        ("medicaments", "0004_swissmedic"),
    ]

    operations = [
        migrations.AddField(
            model_name="patient",
            name="referentiel_medicaments",
            field=models.CharField(
                choices=[("BDPM", "BDPM (France)"), ("SWISSMEDIC", "Swissmedic (Suisse)")],
                default="BDPM",
                help_text="Référentiel de médicaments utilisé pour ce patient (France ou Suisse).",
                max_length=20,
            ),
        ),
        migrations.RunPython(deduire_referentiel_existant, migrations.RunPython.noop),
    ]
