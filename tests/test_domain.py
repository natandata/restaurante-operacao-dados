import unittest
from operacao.domain import Cozinha, Produto, RegraInvalida
from operacao.demo import simular


class RegrasTest(unittest.TestCase):
    def setUp(self):
        self.produto = Produto('p', 'Prato fictício', 2590, (('arroz_g', 150), ('feijao_g', 100)))
        self.cozinha = Cozinha((self.produto,), {'arroz_g': 1000, 'feijao_g': 700})

    def test_total_exato_em_centavos(self):
        self.assertEqual(self.cozinha.vender('a', {'p': 3}).total_centavos, 7770)

    def test_consumo(self):
        self.cozinha.vender('a', {'p': 2})
        self.assertEqual(self.cozinha.saldo, {'arroz_g': 700, 'feijao_g': 500})

    def test_sem_estoque_nao_muda_nada(self):
        antes = self.cozinha.saldo
        with self.assertRaises(RegraInvalida): self.cozinha.vender('a', {'p': 9})
        self.assertEqual(antes, self.cozinha.saldo)
        self.assertEqual(len(self.cozinha.vendas), 0)

    def test_pedido_repetido_nao_consume_duas_vezes(self):
        primeira = self.cozinha.vender('a', {'p': 2})
        saldo = self.cozinha.saldo
        self.assertEqual(primeira, self.cozinha.vender('a', {'p': 2}))
        self.assertEqual(saldo, self.cozinha.saldo)
        self.assertEqual(len(self.cozinha.vendas), 1)

    def test_repeticao_com_conteudo_diferente_e_erro(self):
        self.cozinha.vender('a', {'p': 2})
        with self.assertRaises(RegraInvalida): self.cozinha.vender('a', {'p': 1})

    def test_produto_inexistente(self):
        with self.assertRaises(RegraInvalida): self.cozinha.vender('a', {'x': 1})

    def test_quantidade_negativa_zero_fracionada_bool(self):
        for quantidade in (-1, 0, 1.5, True):
            with self.subTest(quantidade=quantidade):
                with self.assertRaises(RegraInvalida):
                    self.cozinha.vender('a', {'p': quantidade})

    def test_saldo_nao_pode_ser_mutado_por_fora(self):
        copia = self.cozinha.saldo
        copia['arroz_g'] = 0
        self.assertEqual(self.cozinha.saldo['arroz_g'], 1000)

    def test_mesma_semente_mesma_simulacao(self):
        self.assertEqual(simular(), simular())

    def test_cenario_tem_aceitos_e_rejeitados(self):
        estados = {e['estado'] for e in simular()['eventos']}
        self.assertEqual(estados, {'aceito', 'rejeitado'})

    def test_saldo_nunca_fica_negativo(self):
        for semente in range(25):
            self.assertTrue(all(v >= 0 for v in simular(semente, 100)['saldo_unidade_base'].values()))

    def test_receita_com_ingrediente_repetido(self):
        with self.assertRaises(RegraInvalida):
            Produto('p', 'Prato', 100, (('arroz_g', 10), ('arroz_g', 20)))

    def test_ingrediente_sem_unidade_de_estoque(self):
        with self.assertRaises(RegraInvalida): Cozinha((self.produto,), {'arroz_g': 1000})

    def test_preco_invalido(self):
        for preco in (0, -10, 2.50, True):
            with self.assertRaises(RegraInvalida): Produto('p', 'Prato', preco, (('arroz_g', 1),))

    def test_catalogo_com_codigo_repetido(self):
        with self.assertRaises(RegraInvalida): Cozinha((self.produto, self.produto), {})

    def test_pedido_vazio(self):
        with self.assertRaises(RegraInvalida): self.cozinha.vender('a', {})
        with self.assertRaises(RegraInvalida): self.cozinha.vender(' ', {'p': 1})

    def test_limite_de_simulacao(self):
        for n in (0, 1001, True):
            with self.assertRaises(ValueError): simular(tentativas=n)


if __name__ == '__main__': unittest.main()
