from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Telemetria
from alertas.models import Alerta


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
    limite = sensor.limite_alerta

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

    def garantir_ordem_servico(nivel_alerta, texto_alerta, motivo):
        from manutencao.models import OrdemServico
        
        # Mapeamento de severidade do Alerta -> Prioridade da O.S. (Alinhado com Model)
        prioridade_map = {
            'critico': 'critico',
            'medio': 'medio',
            'baixo': 'baixo'
        }
        
        prioridade_alvo = prioridade_map.get(nivel_alerta, 'baixo')
        titulo_os = f"MANUTENÇÃO: {tipo_alerta}"
        
        # Verifica se já existe uma O.S. ativa para este equipamento E este problema específico
        os_ativa = OrdemServico.objects.filter(
            equipamento=equipamento,
            status__in=['pendente', 'andamento'],
            titulo=titulo_os
        ).first()

        if not os_ativa:
            # Cria a O.S. se não houver nenhuma ativa para este tipo de problema
            OrdemServico.objects.create(
                equipamento=equipamento,
                titulo=titulo_os,
                descricao=f"O.S. gerada automaticamente ({motivo}).\n{texto_alerta}",
                prioridade=prioridade_alvo,
                status='pendente'
            )
        else:
            # Se a O.S. já existe, verifica se o nível de prioridade precisa subir
            ordem_peso = {'baixo': 1, 'medio': 2, 'critico': 3}
            if ordem_peso[prioridade_alvo] > ordem_peso[os_ativa.prioridade]:
                os_ativa.prioridade = prioridade_alvo
                os_ativa.descricao += f"\n\n[ATUALIZAÇÃO]: Nível escalado para {nivel_alerta.upper()}. {texto_alerta}"
                os_ativa.save()

    if alerta_existente:
        # Só atualiza se o nível piorou (baixo → medio → critico)
        ordem_nivel = {'baixo': 1, 'medio': 2, 'critico': 3}
        if ordem_nivel[nivel] > ordem_nivel[alerta_existente.nivel]:
            alerta_existente.nivel = nivel
            alerta_descricao_escalada = (
                f"Situação agravada em {equipamento.nome} ({equipamento.tipo}). "
                f"Sensor de {sensor.get_tipo_sensor_display()} registrou "
                f"{valor}{sensor.unidade_medida} "
                f"({round(percentual * 100, 1)}% do limite de {limite}{sensor.unidade_medida})."
            )
            alerta_existente.descricao = alerta_descricao_escalada
            alerta_existente.save()

            # Gera ou atualiza a O.S. devido ao agravamento
            garantir_ordem_servico(nivel, alerta_descricao_escalada, "AGRAVAMENTO")
        return

    # Cria novo alerta
    alerta_descricao = (
        f"Anomalia detectada em {equipamento.nome} ({equipamento.tipo}). "
        f"Sensor de {sensor.get_tipo_sensor_display()} registrou "
        f"{valor}{sensor.unidade_medida} "
        f"({round(percentual * 100, 1)}% do limite de {limite}{sensor.unidade_medida})."
    )

    Alerta.objects.create(
        equipamento=equipamento,
        tipo_alerta=tipo_alerta,
        nivel=nivel,
        descricao=alerta_descricao
    )

    # Gera a O.S. inicial para o novo alerta
    garantir_ordem_servico(nivel, alerta_descricao, "NOVO ALERTA")
