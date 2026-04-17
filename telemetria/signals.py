from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Telemetria
from alertas.models import Alerta
from .config_alertas import obter_limite


@receiver(post_save, sender=Telemetria)
def checar_limites_telemetria(sender, instance, created, **kwargs):
    """
    Sistema Preditivo de Alertas — dispara automaticamente a cada nova leitura de sensor.

    Regras de nível (baseadas no % do limite configurado):
        - CRÍTICO  : valor >= 100% do limite
        - MÉDIO    : valor >=  85% do limite (mas < 100%)
        - BAIXO    : valor >=  70% do limite (mas <  85%)
        - Abaixo de 70%: nenhum alerta gerado

    Deduplicação: se já existe um alerta ATIVO para o mesmo equipamento
    e tipo de sensor, não gera um duplicado — apenas atualiza o nível
    se a situação piorou.
    """
    if not created:
        return

    sensor = instance.sensor

    # Sensores desativados não geram alertas
    if not sensor.ativo:
        return

    valor = instance.valor
    equipamento = sensor.equipamento
    limite = obter_limite(equipamento.tipo, sensor.tipo_sensor)

    if limite is None or limite <= 0:
        return

    percentual = valor / limite

    # Determina o nível pelo percentual do limite atingido
    if percentual >= 1.0:
        nivel = 'critico'
    elif percentual >= 0.85:
        nivel = 'medio'
    elif percentual >= 0.70:
        nivel = 'baixo'
    else:
        return  # Valor normal — nenhum alerta necessário

    tipo_alerta = f"Alerta de {sensor.get_tipo_sensor_display()}"

    # Deduplicação: busca alerta ativo do mesmo tipo no mesmo equipamento
    alerta_existente = Alerta.objects.filter(
        equipamento=equipamento,
        tipo_alerta=tipo_alerta,
        status='ativo'
    ).first()

    if alerta_existente:
        # Só atualiza se o nível piorou (baixo → medio → critico)
        ordem_nivel = {'baixo': 1, 'medio': 2, 'critico': 3}
        if ordem_nivel[nivel] > ordem_nivel[alerta_existente.nivel]:
            alerta_existente.nivel = nivel
            alerta_existente.descricao = (
                f"Situação agravada em {equipamento.nome} ({equipamento.tipo}). "
                f"Sensor de {sensor.get_tipo_sensor_display()} registrou "
                f"{valor}{sensor.unidade_medida} "
                f"({round(percentual * 100, 1)}% do limite de {limite}{sensor.unidade_medida})."
            )
            alerta_existente.save()
        return

    # Cria novo alerta
    Alerta.objects.create(
        equipamento=equipamento,
        tipo_alerta=tipo_alerta,
        nivel=nivel,
        descricao=(
            f"Anomalia detectada em {equipamento.nome} ({equipamento.tipo}). "
            f"Sensor de {sensor.get_tipo_sensor_display()} registrou "
            f"{valor}{sensor.unidade_medida} "
            f"({round(percentual * 100, 1)}% do limite de {limite}{sensor.unidade_medida})."
        )
    )
