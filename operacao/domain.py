"""Regras próprias de demonstração. Não atende operação real ou concorrente."""
from dataclasses import dataclass
from typing import Dict, Mapping, Tuple


class RegraInvalida(ValueError):
    pass


def inteiro_positivo(valor: int, campo: str) -> None:
    if type(valor) is not int or valor <= 0:
        raise RegraInvalida(f'{campo} precisa ser um inteiro positivo')


@dataclass(frozen=True)
class Produto:
    codigo: str
    nome: str
    preco_centavos: int
    # Cada ingrediente tem uma unidade-base única, definida no catálogo do cenário.
    receita: Tuple[Tuple[str, int], ...]

    def __post_init__(self):
        if not self.codigo.strip() or not self.nome.strip():
            raise RegraInvalida('Produto precisa de código e nome')
        inteiro_positivo(self.preco_centavos, 'Preço em centavos')
        if not self.receita:
            raise RegraInvalida('Receita vazia')
        if len({item[0] for item in self.receita}) != len(self.receita):
            raise RegraInvalida('Ingrediente repetido na receita')
        for ingrediente, quantidade in self.receita:
            if not ingrediente.strip():
                raise RegraInvalida('Ingrediente sem código')
            inteiro_positivo(quantidade, 'Consumo na unidade-base')


@dataclass(frozen=True)
class Venda:
    pedido: str
    itens: Tuple[Tuple[str, int], ...]
    total_centavos: int
    consumo: Tuple[Tuple[str, int], ...]


class Cozinha:
    """Estado em memória; cada processo tem sua própria cozinha.

    Uma venda aprovada consome o estoque inteiro de forma indivisível.
    Falta de ingrediente rejeita a venda inteira. Não há reserva, cancelamento,
    impostos, descontos ou integração de pagamento neste primeiro módulo.
    """

    def __init__(self, produtos: Tuple[Produto, ...], saldo: Mapping[str, int]):
        if len({p.codigo for p in produtos}) != len(produtos):
            raise RegraInvalida('Código de produto repetido')
        for ingrediente, quantidade in saldo.items():
            if not ingrediente.strip() or type(quantidade) is not int or quantidade < 0:
                raise RegraInvalida('Saldo inicial inválido')
        self._catalogo = {p.codigo: p for p in produtos}
        self._saldo = dict(saldo)
        faltantes = {i for p in produtos for i, _ in p.receita} - self._saldo.keys()
        if faltantes:
            raise RegraInvalida(f'Ingredientes sem saldo declarado: {sorted(faltantes)}')
        self._vendas: Dict[str, Venda] = {}

    @property
    def saldo(self) -> Dict[str, int]:
        return dict(self._saldo)

    @property
    def vendas(self) -> Tuple[Venda, ...]:
        return tuple(self._vendas.values())

    def vender(self, pedido: str, itens: Mapping[str, int]) -> Venda:
        if not isinstance(pedido, str) or not pedido.strip() or not itens:
            raise RegraInvalida('Pedido precisa de identificador e itens')
        for codigo, quantidade in itens.items():
            if codigo not in self._catalogo:
                raise RegraInvalida(f'Produto desconhecido: {codigo}')
            inteiro_positivo(quantidade, 'Quantidade de produto')
        assinatura = tuple(sorted(itens.items()))
        if pedido in self._vendas:
            anterior = self._vendas[pedido]
            if anterior.itens != assinatura:
                raise RegraInvalida('Identificador já usado com itens diferentes')
            return anterior
        consumo: Dict[str, int] = {}
        total = 0
        for codigo, quantidade in assinatura:
            produto = self._catalogo[codigo]
            total += produto.preco_centavos * quantidade
            for ingrediente, porcao in produto.receita:
                consumo[ingrediente] = consumo.get(ingrediente, 0) + porcao * quantidade
        faltantes = [i for i, q in consumo.items() if self._saldo[i] < q]
        if faltantes:
            raise RegraInvalida(f'Estoque insuficiente: {", ".join(sorted(faltantes))}')
        venda = Venda(pedido, assinatura, total, tuple(sorted(consumo.items())))
        # Só altera estado depois de validar o pedido inteiro.
        for ingrediente, quantidade in consumo.items():
            self._saldo[ingrediente] -= quantidade
        self._vendas[pedido] = venda
        return venda
