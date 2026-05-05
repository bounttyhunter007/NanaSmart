import os
import sys
import django

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'app.settings')
django.setup()

from accounts.models import Empresa
from ativos.models import Equipamento, PlanoManutencao
from manutencao.models import OrdemServico


def run():
    print("\n" + "="*60)
    print("TESTANDO MANUTENÇÃO PREDITIVA POR HORÍMETRO")
    print("="*60)

    # --- Setup ---
    Empresa.objects.filter(cnpj='55.555.555/0001-55').delete()
    empresa = Empresa.objects.create(nome='PreditivaCorp', cnpj='55.555.555/0001-55', email='t@t.com')
    motor = Equipamento.objects.create(
        nome='Motor de Teste Preditivo', tipo='Motor Elétrico',
        numero_serie='PRED-001', empresa=empresa, horimetro=200.0
    )

    # --- Plano criado quando equipamento já tem 200h ---
    plano_oleo = PlanoManutencao.objects.create(
        equipamento=motor,
        nome_servico='Troca de Óleo',
        descricao='Drenar o óleo antigo e aplicar óleo 5W40.',
        intervalo_horas=100.0,
        prioridade='medio'
    )
    plano_rolamento = PlanoManutencao.objects.create(
        equipamento=motor,
        nome_servico='Revisão de Rolamentos',
        descricao='Verificar e substituir rolamentos se necessário.',
        intervalo_horas=250.0,
        prioridade='critico'
    )

    print(f"\n[SETUP] Motor criado com {motor.horimetro}h.")
    print(f"[SETUP] Plano 'Troca de Óleo': dispara a cada 100h. Próximo disparo: {plano_oleo.horimetro_ultima_os + plano_oleo.intervalo_horas}h")
    print(f"[SETUP] Plano 'Revisão de Rolamentos': dispara a cada 250h. Próximo disparo: {plano_rolamento.horimetro_ultima_os + plano_rolamento.intervalo_horas}h")

    # --- TESTE 1: Atualizar para 250h (apenas Troca de Óleo deve disparar) ---
    print("\n[1/4] Atualizando horímetro para 250h...")
    motor.horimetro = 250.0
    motor.save()
    os_geradas = OrdemServico.objects.filter(equipamento=motor, tipo_os='preditiva')
    if os_geradas.filter(titulo__contains='Troca de Óleo').exists():
        print("[OK] O.S. de 'Troca de Óleo' gerada (200 + 100 = 300 > 250? Não... 250 >= 300? Não!)")
    
    # Corrigindo: 200 (base) + 100 (intervalo) = 300. 250 < 300, não deve gerar.
    if not os_geradas.exists():
        print("[OK] Nenhuma O.S. gerada para 250h (correto: próximo disparo é em 300h).")
    else:
        print(f"[ERRO] O.S. gerada inesperadamente em 250h: {[o.titulo for o in os_geradas]}")

    # --- TESTE 2: Atualizar para 310h (Troca de Óleo deve disparar) ---
    print("\n[2/4] Atualizando horímetro para 310h...")
    motor.horimetro = 310.0
    motor.save()
    os_oleo = OrdemServico.objects.filter(equipamento=motor, tipo_os='preditiva', titulo__contains='Troca de Óleo')
    if os_oleo.exists():
        print(f"[OK] O.S. 'Troca de Óleo' criada! ID #{os_oleo.first().id} | Prioridade: {os_oleo.first().prioridade}")
    else:
        print("[ERRO] O.S. de Troca de Óleo NÃO foi criada!")

    # --- TESTE 3: Atualizar para 315h (não deve duplicar) ---
    print("\n[3/4] Atualizando horímetro para 315h (teste anti-duplicação)...")
    motor.horimetro = 315.0
    motor.save()
    total = OrdemServico.objects.filter(equipamento=motor, tipo_os='preditiva', titulo__contains='Troca de Óleo').count()
    if total == 1:
        print(f"[OK] Anti-duplicação funcionando! Ainda há apenas 1 O.S. de Troca de Óleo.")
    else:
        print(f"[ERRO] Duplicação detectada! Existem {total} O.S. de Troca de Óleo.")

    # --- TESTE 4: Atualizar para 460h (Rolamento deve disparar, Óleo deve gerar uma segunda) ---
    print("\n[4/4] Atualizando horímetro para 460h (Rolamento e 2ª Troca de Óleo)...")
    # Primeiro: concluir a O.S. de óleo para liberar o próximo ciclo
    primeira_os_oleo = os_oleo.first()
    primeira_os_oleo.status = 'concluida'
    primeira_os_oleo.save()

    motor.horimetro = 460.0
    motor.save()

    total_oleo = OrdemServico.objects.filter(equipamento=motor, tipo_os='preditiva', titulo__contains='Troca de Óleo').count()
    total_rolamento = OrdemServico.objects.filter(equipamento=motor, tipo_os='preditiva', titulo__contains='Rolamentos').count()

    if total_oleo == 2:
        print(f"[OK] 2ª O.S. de 'Troca de Óleo' gerada! (Ciclo correto: 310 + 100 = 410h <= 460h)")
    else:
        print(f"[INFO] O.S. de Troca de Óleo: {total_oleo} (esperado 2)")

    if total_rolamento == 1:
        print(f"[OK] O.S. de 'Revisão de Rolamentos' gerada! (200 + 250 = 450h <= 460h)")
    else:
        print(f"[ERRO] O.S. de Rolamento não gerada. Total: {total_rolamento}")

    print("\n" + "="*60)
    print(f"RESUMO: {OrdemServico.objects.filter(equipamento=motor, tipo_os='preditiva').count()} O.S. preditivas geradas no total.")
    print("="*60 + "\n")


if __name__ == '__main__':
    run()
