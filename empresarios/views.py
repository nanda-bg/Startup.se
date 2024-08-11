from datetime import datetime
from pyexpat.errors import messages
import re
from django.shortcuts import redirect, render
from investidores.models import PropostaInvestimento
from .models import Documento, Empresas, Metricas
from django.contrib import messages
from django.contrib.messages import constants
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError

import locale
locale.setlocale(locale.LC_ALL, 'pt_BR.UTF-8')

@login_required(login_url='http://127.0.0.1:8000/usuarios/logar/')
def cadastrar_empresa(request):
    if request.method == "GET":
        return render(request, 'cadastrar_empresa.html', 
                      {'tempo_existencia': Empresas.tempo_existencia_choices,
                       'areas': Empresas.area_choices})

    elif request.method == "POST":
        nome = request.POST.get('nome')
        cnpj = request.POST.get('cnpj')
        site = request.POST.get('site')
        tempo_existencia = request.POST.get('tempo_existencia')
        descricao = request.POST.get('descricao')
        data_final = request.POST.get('data_final')
        percentual_equity = request.POST.get('percentual_equity')
        estagio = request.POST.get('estagio')
        area = request.POST.get('area')
        publico_alvo = request.POST.get('publico_alvo')
        valor = request.POST.get('valor')
        pitch = request.FILES.get('pitch')
        logo = request.FILES.get('logo')


        if not nome:
            messages.add_message(request, constants.ERROR, 'Nome é obrigatório')
            return redirect('/empresarios/cadastrar_empresa')

        cnpj = re.sub(r'\D', '', cnpj)
        if not re.match(r'^\d{14}$', cnpj):
            messages.add_message(request, constants.ERROR, 'CNPJ inválido')
            return redirect('/empresarios/cadastrar_empresa')

        if site:
            if not re.match(r'^(https?://)?([a-zA-Z0-9-]+\.)+[a-zA-Z]{2,6}(/.*)?$', site):
                messages.add_message(request, constants.ERROR, 'Site inválido')
                return redirect('/empresarios/cadastrar_empresa')
            if not re.match(r'^https?://', site):
                site = 'http://' + site

        if not descricao or len(descricao) < 10:
            messages.add_message(request, constants.ERROR, 'Descrição deve ter pelo menos 10 caracteres')
            return redirect('/empresarios/cadastrar_empresa')

        try:
            percentual_equity = float(percentual_equity)
            if not (0 <= percentual_equity <= 100):
                raise ValueError()
        except ValueError:
            messages.add_message(request, constants.ERROR, 'Percentual de equity inválido')
            return redirect('/empresarios/cadastrar_empresa')

        try:
            valor = float(valor)
        except ValueError:
            messages.add_message(request, constants.ERROR, 'Valor inválido')
            return redirect('/empresarios/cadastrar_empresa')
        
        try:
            data_final_datetime = datetime.strptime(data_final, '%Y-%m-%d')
            if data_final_datetime < datetime.now():
                messages.add_message(request, constants.ERROR, 'A data final de captação não pode ser anterior à data atual')
                return redirect('/empresarios/cadastrar_empresa')
        except ValueError:
            messages.add_message(request, constants.ERROR, 'Formato de data inválido')
            return redirect('/empresarios/cadastrar_empresa')

        if tempo_existencia not in dict(Empresas.tempo_existencia_choices).keys():
            messages.add_message(request, constants.ERROR, 'Tempo de existência inválido')
            return redirect('/empresarios/cadastrar_empresa')

        if estagio not in dict(Empresas.estagio_choices).keys():
            messages.add_message(request, constants.ERROR, 'Estágio inválido')
            return redirect('/empresarios/cadastrar_empresa')

        if area not in dict(Empresas.area_choices).keys():
            messages.add_message(request, constants.ERROR, 'Área inválida')
            return redirect('/empresarios/cadastrar_empresa')


        try:
            empresa = Empresas(
                user=request.user,
                nome=nome,
                cnpj=cnpj,
                site=site,
                tempo_existencia=tempo_existencia,
                descricao=descricao,
                data_final_captacao=data_final,
                percentual_equity=percentual_equity,
                estagio=estagio,
                area=area,
                publico_alvo=publico_alvo,
                valor=valor,
                pitch=pitch,
                logo=logo
            )
            empresa.save()
        except:
            messages.add_message(request, constants.ERROR, 'Erro interno do sistema')
            return redirect('/empresarios/cadastrar_empresa')
        
        messages.add_message(request, constants.SUCCESS, 'Empresa criada com sucesso')
        return redirect('/empresarios/cadastrar_empresa')
    

@login_required(login_url='http://127.0.0.1:8000/usuarios/logar/')    
def listar_empresas(request):
    if request.method == "GET":
        busca = request.GET.get('empresa', '')
        if busca:
            empresas = Empresas.objects.filter(user=request.user, nome__icontains=busca)
        else:
            empresas = Empresas.objects.filter(user=request.user)

        return render(request, 'listar_empresas.html', {'empresas': empresas})

@login_required(login_url='http://127.0.0.1:8000/usuarios/logar/')
def empresa(request, id):
    empresa = Empresas.objects.get(id=id)

    if empresa.user != request.user:
        if request.user.is_authenticated:
            messages.add_message(request, constants.ERROR, 'Acesso negado')
        return redirect('/empresarios/listar_empresas')
    
    if request.method == "GET":
        documentos = Documento.objects.filter(empresa=empresa)

        proposta_investimentos = PropostaInvestimento.objects.filter(empresa=empresa)

        percentual_vendido = 0
        for proposta in proposta_investimentos:
            if proposta.status == 'PA':
                percentual_vendido += proposta.percentual

        total_captado = sum(proposta_investimentos.filter(status='PA').values_list('valor', flat=True))
        total_captado_formatado = locale.format_string('%.2f', total_captado, grouping=True)


        valuation_atual = (100 * float(total_captado)) / float(percentual_vendido) if percentual_vendido > 0 else 0
        valuation_atual_formatado = locale.format_string('%.2f', valuation_atual, grouping=True)

        valuation_esperado_formatado = locale.format_string('%.2f', float(empresa.valuation), grouping=True)

        proposta_investimentos_enviada = proposta_investimentos.filter(status='PE')

        metricas = Metricas.objects.filter(empresa = empresa)

        return render(request, 'empresa.html', {'empresa': empresa, 
                                                'documentos': documentos, 
                                                'proposta_investimentos_enviada': proposta_investimentos_enviada, 
                                                'percentual_vendido': int(percentual_vendido), 
                                                'total_captado': total_captado_formatado,
                                                'valuation_atual': valuation_atual_formatado,
                                                'valuation_esperado': valuation_esperado_formatado,
                                                "metricas": metricas})
    

@login_required(login_url='http://127.0.0.1:8000/usuarios/logar/')    
def add_doc(request, id):
    empresa = Empresas.objects.get(id=id)
    titulo = request.POST.get('titulo')
    arquivo = request.FILES.get('arquivo')

    if empresa.user != request.user:
        messages.add_message(request, constants.ERROR, 'Acesso negado')
        return redirect('/empresarios/listar_empresas')


    if not arquivo:
        messages.add_message(request, constants.ERROR, 'O arquivo não pode estar vazio')
        return redirect(f'/empresarios/empresa/{id}')
    
    extensao  = arquivo.name.split('.')

    if extensao[-1] != 'pdf':
        messages.add_message(request, constants.ERROR, 'O arquivo deve estar em PDF')
        return redirect(f'/empresarios/empresa/{id}')


    documento = Documento(empresa = empresa,
                          titulo = titulo,
                          arquivo = arquivo)
    
    documento.save()

    messages.add_message(request, constants.SUCCESS, 'Arquivo cadastrado com sucesso!')
    return redirect(f'/empresarios/empresa/{id}')


@login_required(login_url='http://127.0.0.1:8000/usuarios/logar/')
def excluir_dc(request, id):
    documento = Documento.objects.get(id=id)

    if documento.empresa.user != request.user:
        messages.add_message(request, constants.ERROR, "Acesso negado")
        return redirect(f'/empresarios/empresa/{documento.empresa.id}')

    documento.delete()

    messages.add_message(request, constants.SUCCESS, 'Documento excluído com sucesso!')

    return redirect(f'/empresarios/empresa/{documento.empresa.id}')

@login_required(login_url='http://127.0.0.1:8000/usuarios/logar/')
def add_metrica(request, id):
    empresa = Empresas.objects.get(id = id)
    titulo = request.POST.get('titulo')
    valor = request.POST.get('valor')

    metrica = Metricas(empresa = empresa,
                       titulo = titulo,
                       valor = valor)
    
    metrica.save()

    messages.add_message(request, constants.SUCCESS, 'Métrica cadastrada com sucesso!')
    return redirect(f'/empresarios/empresa/{empresa.id}')
    
@login_required(login_url='http://127.0.0.1:8000/usuarios/logar/')
def excluir_metrica(request, id):
    metrica = Metricas.objects.get(id = id)

    if metrica.empresa.user != request.user:
        messages.add_message(request, constants.ERROR, "Acesso negado")
        return redirect(f'/empresarios/empresa/{metrica.empresa.id}')

    metrica.delete()

    messages.add_message(request, constants.SUCCESS, 'Métrica excluída com sucesso!')

    return redirect(f'/empresarios/empresa/{metrica.empresa.id}')

@login_required(login_url='http://127.0.0.1:8000/usuarios/logar/')
def gerenciar_proposta(request, id):
    acao = request.GET.get('acao')
    proposta = PropostaInvestimento.objects.get(id = id)
    empresa = proposta.empresa

    if acao == 'aceitar':
        messages.add_message(request, constants.SUCCESS, 'Proposta aceita')
        proposta.status = 'PA'
    elif acao == 'negar':
        messages.add_message(request, constants.SUCCESS, 'Proposta recusada')
        proposta.status = 'PR'

    proposta.save()
    
    return redirect(f'/empresarios/empresa/{empresa.id}')