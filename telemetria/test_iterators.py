from unittest.mock import Mock

from django.test import SimpleTestCase

from .iterators import IteradorLeituras


class IteradorLeiturasTests(SimpleTestCase):
    def test_single_pass_keeps_values_order_and_stop_iteration(self):
        rows = [{'valor': 3}, {'valor': 2}, {'valor': 1}]
        queryset = Mock()
        queryset.iterator.return_value = iter(rows)
        iterator = IteradorLeituras(queryset)
        self.assertIs(iter(iterator), iterator)
        self.assertIs(next(iterator), rows[0])
        self.assertEqual(list(iterator), rows[1:])
        with self.assertRaises(StopIteration):
            next(iterator)
        queryset.iterator.assert_called_once_with(chunk_size=500)

    def test_iteration_does_not_consume_the_query_in_the_constructor(self):
        visited = []

        def source():
            for value in range(3):
                visited.append(value)
                yield {'valor': value}

        queryset = Mock()
        queryset.iterator.return_value = source()
        iterator = IteradorLeituras(queryset, chunk_size=2)
        self.assertEqual(visited, [])
        self.assertEqual(next(iterator), {'valor': 0})
        self.assertEqual(visited, [0])
        queryset.iterator.assert_called_once_with(chunk_size=2)

    def test_source_failures_are_not_swallowed(self):
        def source():
            yield {'valor': 1}
            raise RuntimeError('falha na leitura')

        queryset = Mock()
        queryset.iterator.return_value = source()
        iterator = IteradorLeituras(queryset)
        self.assertEqual(next(iterator), {'valor': 1})
        with self.assertRaisesRegex(RuntimeError, 'falha na leitura'):
            next(iterator)
