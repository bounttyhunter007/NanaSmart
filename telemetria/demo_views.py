"""API administrativa; nenhuma leitura ou relógio é fornecido pelo cliente."""
from rest_framework import serializers
from rest_framework.permissions import BasePermission
from rest_framework.views import APIView
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema, OpenApiResponse
from .models import TrendDemo
from .demo_service import create_demo, update_demo, snapshot
from .demo_serializers import DemoRequest, DemoCreateRequest, DemoUpdateRequest, TrendDemoSnapshotSerializer


class DemoAdminPermission(BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.tipo_usuario == 'admin')


class TrendDemoView(APIView):
    permission_classes = [DemoAdminPermission]

    @extend_schema(
        operation_id='telemetria_demo_atual',
        responses={200: OpenApiResponse(
            response=TrendDemoSnapshotSerializer,
            description='Última demonstração do administrador. Sem demonstração, retorna 200 sem corpo.',
        )},
    )
    def get(self, request, demo_id=None):
        if demo_id:
            demo = get_object_or_404(TrendDemo, pk=demo_id, owner=request.user)
        else:
            demo = TrendDemo.objects.filter(owner=request.user).order_by('-criado_em').first()
        return Response(snapshot(demo) if demo else None)

    @extend_schema(
        operation_id='telemetria_demo_criar',
        request=DemoCreateRequest,
        responses={201: TrendDemoSnapshotSerializer},
    )
    def post(self, request, demo_id=None):
        data = DemoRequest(data=request.data)
        data.is_valid(raise_exception=True)
        values = data.validated_data
        if demo_id:
            return Response(update_demo(request.user, demo_id, values['acao'], values.get('cenario')))
        if 'empresa' not in values:
            raise serializers.ValidationError({'empresa': 'Selecione uma empresa.'})
        return Response(create_demo(request.user, values['empresa'], values.get('cenario', 'aumento')), status=201)


class TrendDemoDetailView(TrendDemoView):
    @extend_schema(
        operation_id='telemetria_demo_consultar',
        responses=TrendDemoSnapshotSerializer,
    )
    def get(self, request, demo_id):
        return super().get(request, demo_id=demo_id)

    @extend_schema(
        operation_id='telemetria_demo_atualizar',
        request=DemoUpdateRequest,
        responses=TrendDemoSnapshotSerializer,
    )
    def post(self, request, demo_id):
        return super().post(request, demo_id=demo_id)
