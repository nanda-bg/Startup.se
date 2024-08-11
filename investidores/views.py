import locale
locale.setlocale(locale.LC_ALL, 'pt_BR.UTF-8')

from django.http import Http404
from django.shortcuts import redirect, render
from django.contrib.auth.decorators import login_required
from empresarios.models import Empresas, Documento, Metricas
from investidores.models import PropostaInvestimento
from django.contrib import messages
from django.contrib.messages import constants

@login_required(login_url='http://127.0.0.1:8000/usuarios/logar/')
def sugestao(request):
    areas = Empresas.area_choices

    if request.method == "GET":   
        return render(request, 'sugestao.html', {'areas': areas})
    
    elif request.method == "POST":
        tipo = request.POST.get('tipo')
        area = request.POST.getlist('area')
        valor = request.POST.get('valor')

        if tipo == 'C':
            empresas = Empresas.objects.filter(tempo_existencia = '+5').filter(estagio = "E")
        elif tipo == 'D':
            empresas = Empresas.objects.filter(tempo_existencia__in = ['-6', '+6', '+1']).exclude(estagio = "E")

        #Tipo genérico de investidor
        
        empresas = empresas.filter(area__in = area)
        
        empresas_selecionadas = []
        for empresa in empresas:
            percentual = (float(valor) * 100) / float(empresa.valuation)
            if percentual >= 1:
                empresas_selecionadas.append(empresa)

        return render(request, 'sugestao.html', {'empresas': empresas_selecionadas, 'areas': areas})

@login_required(login_url='http://127.0.0.1:8000/usuarios/logar/')
def ver_empresa(request, id):
    empresa = Empresas.objects.get(id = id)
    documentos = Documento.objects.filter(empresa=empresa)
    proposta_investimentos = PropostaInvestimento.objects.filter(empresa = empresa).filter(status = 'PA')

    percentual_vendido = 0
    for proposta in proposta_investimentos:
        percentual_vendido += proposta.percentual

    limiar = empresa.percentual_equity * 0.8
    concretizado = False

    if percentual_vendido >= limiar:
        concretizado = True

    percentual_disponivel = empresa.percentual_equity - percentual_vendido

    valuation_esperado_formatado = locale.format_string('%.2f', float(empresa.valuation), grouping=True)

    #listar as métricas
    metricas = Metricas.objects.filter(empresa = empresa)


    return render(request, 'ver_empresa.html', {'empresa': empresa, 
                                                'documentos': documentos,
                                                'percentual_vendido': int(percentual_vendido),
                                                'concretizado': concretizado,
                                                'percentual_disponivel': percentual_disponivel,
                                                'valuation_esperado': valuation_esperado_formatado,
                                                'metricas': metricas})

@login_required(login_url='http://127.0.0.1:8000/usuarios/logar/')
def realizar_proposta(request, id):
    valor = request.POST.get('valor')
    percentual = request.POST.get('percentual')
    empresa = Empresas.objects.get(id = id)

    propostas_aceitas = PropostaInvestimento.objects.filter(empresa = empresa).filter(status = 'PA')

    total = 0
    for pa in propostas_aceitas:
        total += pa.percentual

    if total + float(percentual) > empresa.percentual_equity:
        messages.add_message(request, constants.WARNING, "O percentual solicitado é maior do que o disponível para compra")
        return redirect(f'/investidores/ver_empresa/{empresa.id}')
    

    valuation = (100 * float(valor)) / float(percentual)
    if valuation < float(empresa.valuation)/2:
        messages.add_message(request, constants.WARNING, f"O valuation mínimo é de R${empresa.valuation}")
        return redirect(f'/investidores/ver_empresa/{empresa.id}')


    proposta = PropostaInvestimento(
        valor = valor,
        percentual = percentual,
        empresa = empresa,
        investidor = request.user
    )

    proposta.save()

    return redirect(f'/investidores/assinar_contrato/{proposta.id}')

@login_required(login_url='http://127.0.0.1:8000/usuarios/logar/')
def assinar_contrato(request, id):
    proposta = PropostaInvestimento.objects.get(id=id)
    if proposta.status != "AS":
        raise Http404()
    
    if request.method == "GET":
        return render(request, 'assinar_contrato.html', {'proposta': proposta})
    
    elif request.method == "POST":
        selfie = request.FILES.get('selfie')
        rg = request.FILES.get('rg')
        

        #Validação se rg e selfie são da msm pessoa
        

        proposta.selfie = selfie
        proposta.rg = rg
        proposta.status = 'PE'
        proposta.save()

        messages.add_message(request, constants.SUCCESS, f'Contrato assinado com sucesso, sua proposta foi enviada a empresa.')
        return redirect(f'/investidores/ver_empresa/{proposta.empresa.id}')
