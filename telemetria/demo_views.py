"""API administrativa; nenhuma leitura ou relógio é fornecido pelo cliente."""
from rest_framework import serializers
from rest_framework.permissions import BasePermission
from rest_framework.views import APIView
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from .models import TrendDemo
from .demo_service import create_demo, update_demo, snapshot, VALUES


class DemoAdminPermission(BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.tipo_usuario == 'admin')


class DemoRequest(serializers.Serializer):
    empresa = serializers.IntegerField(min_value=1, required=False)
    acao = serializers.ChoiceField(choices=['avancar', 'parar', 'fase'], default='avancar')
    cenario = serializers.ChoiceField(choices=list(VALUES), required=False)


class TrendDemoView(APIView):
    permission_classes = [DemoAdminPermission]

    def get(self, request, demo_id=None):
        if demo_id:
            demo = get_object_or_404(TrendDemo, pk=demo_id, owner=request.user)
        else:
            demo = TrendDemo.objects.filter(owner=request.user).order_by('-criado_em').first()
        return Response(snapshot(demo) if demo else None)

    def post(self, request, demo_id=None):
        data = DemoRequest(data=request.data)
        data.is_valid(raise_exception=True)
        values = data.validated_data
        if demo_id:
            return Response(update_demo(request.user, demo_id, values['acao'], values.get('cenario')))
        if 'empresa' not in values:
            raise serializers.ValidationError({'empresa': 'Selecione uma empresa.'})
        return Response(create_demo(request.user, values['empresa'], values.get('cenario', 'aumento')), status=201)
