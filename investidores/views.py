from datetime import date
import locale
import math

try:
    locale.setlocale(locale.LC_ALL, 'pt_BR')
except locale.Error:
    locale.setlocale(locale.LC_ALL, '')

from django.http import Http404
from django.shortcuts import redirect, render
from django.contrib.auth.decorators import login_required
from empresarios.models import Empresas, Documento, Metricas
from investidores.models import PropostaInvestimento
from django.contrib import messages
from django.contrib.messages import constants
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
import requests
import os


@login_required(login_url='http://127.0.0.1:8000/usuarios/logar/')
def sugestao(request):
    areas = Empresas.area_choices

    if request.method == "GET":   
        empresas = Empresas.objects.all()
        return render(request, 'sugestao.html', {'areas': areas,
                                                 'empresas': empresas})
    
    elif request.method == "POST":
        tipo = request.POST.get('tipo')
        area = request.POST.getlist('area')
        valor = request.POST.get('valor')


        if tipo == 'C':
            empresas = Empresas.objects.filter(tempo_existencia='+5').filter(estagio='E')
        elif tipo == 'M': 
            empresas = Empresas.objects.filter(tempo_existencia__in=['+1', '+5']).filter(estagio__in=['MVPP', 'MVP', 'E'])
        elif tipo == 'D':
            empresas = Empresas.objects.filter(tempo_existencia__in=['-6', '+6', '+1']).exclude(estagio='E')

        
        empresas = empresas.filter(area__in = area).filter(data_final_captacao__lte = date.today())
        
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

    percentual_comprado = (percentual_vendido/empresa.percentual_equity) * 100

    valuation_esperado_formatado = locale.format_string('%.2f', math.ceil(float(empresa.valuation)), grouping=True)

    metricas = Metricas.objects.filter(empresa = empresa)


    return render(request, 'ver_empresa.html', {'empresa': empresa, 
                                                'documentos': documentos,
                                                'percentual_vendido': int(percentual_vendido),
                                                'concretizado': concretizado,
                                                'percentual_disponivel': percentual_disponivel,
                                                'valuation_esperado': valuation_esperado_formatado,
                                                'metricas': metricas,
                                                'percentual_comprado': int(percentual_comprado)})

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
        messages.add_message(request, constants.WARNING, 
                                 f"O valuation mínimo é de R${'{:,.2f}'.format(math.ceil(float(empresa.valuation)/200)).replace(',', 'X').replace('.', ',').replace('X', '.')}")
        return redirect(f'/investidores/ver_empresa/{empresa.id}')


    proposta = PropostaInvestimento(
        valor = valor,
        percentual = percentual,
        empresa = empresa,
        investidor = request.user,
        data = date.today()
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

        if not selfie or not rg:
            messages.add_message(request, constants.ERROR, 'Por favor, envie ambos os arquivos de selfie e RG.')
            return redirect(f'/investidores/ver_empresa/{proposta.empresa.id}')

        # Salvar imagens temporariamente
        selfie_path = 'temp_selfie.jpg'
        rg_path = 'temp_rg.jpg'

        # Salvar arquivos usando default_storage
        default_storage.save(selfie_path, ContentFile(selfie.read()))
        default_storage.save(rg_path, ContentFile(rg.read()))

        # Verificar se os arquivos foram salvos
        if not default_storage.exists(selfie_path) or not default_storage.exists(rg_path):
            messages.add_message(request, constants.ERROR, 'Erro ao salvar arquivos temporários.')
            return redirect(f'/investidores/ver_empresa/{proposta.empresa.id}')
        
        # URL da API Face++
        api_key = 'E6yXYrJOML9N_g-RiITbHScD2oCEiXno'
        api_secret = 'rYnxB7GfXcub2dSfYBxw_2jfB7BB-EgL'
        url = 'https://api-us.faceplusplus.com/facepp/v3/compare'

        # Fazer upload das imagens para o Face++
        with default_storage.open(selfie_path, 'rb') as file_selfie, default_storage.open(rg_path, 'rb') as file_rg:
            response = requests.post(
                url,
                data={
                    'api_key': api_key,
                    'api_secret': api_secret
                },
                files={
                    'image_file1': file_selfie,
                    'image_file2': file_rg
                }
            )
        
        result = response.json()

        # Remover arquivos temporários
        default_storage.delete(selfie_path)
        default_storage.delete(rg_path)

        # Verificar o resultado
        if result.get('confidence', 0) > 80: 
            proposta.selfie = selfie
            proposta.rg = rg
            proposta.status = 'PE'
            proposta.save()
            messages.add_message(request, constants.SUCCESS, 'Contrato assinado com sucesso, sua proposta foi enviada a empresa.')
        else:
            messages.add_message(request, constants.WARNING, 'Erro de validação, tente novamente.')

        return redirect(f'/investidores/ver_empresa/{proposta.empresa.id}')