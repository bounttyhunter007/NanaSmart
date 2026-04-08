from django.urls import path
from .views import KpiDashboardView, DashboardSummaryView

urlpatterns = [
    path('kpis/', KpiDashboardView.as_view(), name='kpi-dashboard'),
    path('resumo/', DashboardSummaryView.as_view(), name='dashboard-summary'),
]
