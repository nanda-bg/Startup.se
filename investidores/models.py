from django.db import models
from empresarios.models import Empresas
from django.contrib.auth.models import User
from django.utils import timezone

class PropostaInvestimento(models.Model):
    status_choices = (
        ('AS', 'Aguardando assinatura'),
        ('PE', 'Proposta enviada'),
        ('PA', 'Proposta aceita'),
        ('PR', 'Proposta recusada')
    )
    valor = models.DecimalField(max_digits=9, decimal_places=2)
    percentual = models.FloatField()
    empresa = models.ForeignKey(Empresas, on_delete=models.CASCADE)
    investidor = models.ForeignKey(User, on_delete=models.CASCADE)
    status = models.CharField(max_length=2, choices=status_choices, default='AS')
    data = models.DateField()
    selfie = models.FileField(upload_to="selfie", null=True, blank=True)
    rg = models.FileField(upload_to="rg", null=True, blank=True)

    def __str__(self):
        return str(self.valor)
    
    @property
    def valuation(self):
        return((100 * float(self.valor)) / self.percentual)