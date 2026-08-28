from django.urls import path

from .views import VerificationInteractionsView

urlpatterns = [
    path(
        "patients/<uuid:patient_id>/verifier-interactions/",
        VerificationInteractionsView.as_view(),
        name="verifier-interactions",
    ),
]
