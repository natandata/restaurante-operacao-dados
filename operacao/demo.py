"""Gera um turno fictício sem escrever arquivos ou acessar rede."""
import argparse
import json
import random
from .domain import Cozinha, Produto, RegraInvalida


def simular(semente=731, tentativas=12):
    if type(tentativas) is not int or not 1 <= tentativas <= 1000:
        raise ValueError('Use de 1 a 1000 tentativas')
    produtos = (
        Produto('prato', 'Prato da casa fictício', 2800, (('arroz_g', 160), ('feijao_g', 130))),
        Produto('porcao', 'Porção de arroz fictícia', 900, (('arroz_g', 180),)),
    )
    cozinha = Cozinha(produtos, {'arroz_g': 2200, 'feijao_g': 1400})
    aleatorio = random.Random(semente)
    eventos = []
    for numero in range(1, tentativas + 1):
        itens = {aleatorio.choice(('prato', 'porcao')): aleatorio.randint(1, 3)}
        pedido = f'DEMO-{numero:03d}'
        try:
            venda = cozinha.vender(pedido, itens)
            eventos.append({'pedido': pedido, 'itens': itens, 'estado': 'aceito',
                            'total_centavos': venda.total_centavos})
        except RegraInvalida as erro:
            eventos.append({'pedido': pedido, 'itens': itens, 'estado': 'rejeitado',
                            'motivo': str(erro)})
    return {'aviso': 'DADOS SINTÉTICOS. Primeiro módulo, não aplicação completa.',
            'semente': semente, 'eventos': eventos, 'saldo_unidade_base': cozinha.saldo,
            'receita_centavos': sum(v.total_centavos for v in cozinha.vendas)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--semente', type=int, default=731)
    parser.add_argument('--tentativas', type=int, default=12)
    args = parser.parse_args()
    print(json.dumps(simular(args.semente, args.tentativas), ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
