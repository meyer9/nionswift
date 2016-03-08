# futures
from __future__ import absolute_import

# standard libraries
import contextlib
import copy
import logging
import random
import unittest
import uuid

# third party libraries
import numpy
import scipy

# local libraries
from nion.data import Calibration
from nion.data import Image
from nion.swift import Application
from nion.swift import DocumentController
from nion.swift.model import DataItem
from nion.swift.model import DocumentModel
from nion.swift.model import Region
from nion.swift.model import Symbolic
from nion.ui import Geometry
from nion.ui import Test


class TestSymbolicClass(unittest.TestCase):

    def setUp(self):
        self.app = Application.Application(Test.UserInterface(), set_global=False)

    def tearDown(self):
        pass

    def test_unary_inversion_returns_inverted_data(self):
        document_model = DocumentModel.DocumentModel()
        with contextlib.closing(document_model):
            d = numpy.zeros((8, 8), dtype=numpy.uint32)
            d[:] = random.randint(1, 100)
            data_item = DataItem.DataItem(d)
            document_model.append_data_item(data_item)
            computation = Symbolic.Computation()
            computation.create_object("a", document_model.get_object_specifier(data_item, "data"))
            computation.parse_expression(document_model, "-a", dict())
            data = computation.evaluate().data
            assert numpy.array_equal(data, -d)

    def test_binary_addition_returns_added_data(self):
        document_model = DocumentModel.DocumentModel()
        with contextlib.closing(document_model):
            d1 = numpy.zeros((8, 8), dtype=numpy.uint32)
            d1[:] = random.randint(1, 100)
            data_item1 = DataItem.DataItem(d1)
            d2 = numpy.zeros((8, 8), dtype=numpy.uint32)
            d2[:] = random.randint(1, 100)
            data_item2 = DataItem.DataItem(d2)
            document_model.append_data_item(data_item1)
            document_model.append_data_item(data_item2)
            computation = Symbolic.Computation()
            computation.create_object("a", document_model.get_object_specifier(data_item1, "data"))
            computation.create_object("b", document_model.get_object_specifier(data_item2, "data"))
            computation.parse_expression(document_model, "a+b", dict())
            data = computation.evaluate().data
            assert numpy.array_equal(data, d1 + d2)

    def test_binary_multiplication_with_scalar_returns_multiplied_data(self):
        document_model = DocumentModel.DocumentModel()
        with contextlib.closing(document_model):
            d = numpy.zeros((8, 8), dtype=numpy.uint32)
            d[:] = random.randint(1, 100)
            data_item = DataItem.DataItem(d)
            document_model.append_data_item(data_item)
            computation1 = Symbolic.Computation()
            computation1.create_object("a", document_model.get_object_specifier(data_item, "data"))
            computation1.parse_expression(document_model, "a * 5", dict())
            data1 = computation1.evaluate().data
            computation2 = Symbolic.Computation()
            computation2.create_object("a", document_model.get_object_specifier(data_item, "data"))
            computation2.parse_expression(document_model, "5 * a", dict())
            data2 = computation1.evaluate().data
            assert numpy.array_equal(data1, d * 5)
            assert numpy.array_equal(data2, d * 5)

    def test_subtract_min_returns_subtracted_min(self):
        document_model = DocumentModel.DocumentModel()
        with contextlib.closing(document_model):
            d = numpy.zeros((8, 8), dtype=numpy.uint32)
            d[:] = random.randint(1, 100)
            data_item = DataItem.DataItem(d)
            document_model.append_data_item(data_item)
            computation = Symbolic.Computation()
            computation.create_object("a", document_model.get_object_specifier(data_item, "data"))
            computation.parse_expression(document_model, "a - amin(a)", dict())
            data = computation.evaluate().data
            assert numpy.array_equal(data, d - numpy.amin(d))

    def test_ability_to_take_slice(self):
        document_model = DocumentModel.DocumentModel()
        with contextlib.closing(document_model):
            d = numpy.zeros((4, 8, 8), dtype=numpy.uint32)
            d[:] = random.randint(1, 100)
            data_item = DataItem.DataItem(d)
            document_model.append_data_item(data_item)
            computation = Symbolic.Computation()
            computation.create_object("a", document_model.get_object_specifier(data_item, "data"))
            computation.parse_expression(document_model, "a[:,4,4]", dict())
            data = computation.evaluate().data
            assert numpy.array_equal(data, d[:,4,4])

    def test_slice_with_empty_dimension_produces_error(self):
        document_model = DocumentModel.DocumentModel()
        with contextlib.closing(document_model):
            d = numpy.zeros((4, 8, 8), dtype=numpy.uint32)
            d[:] = random.randint(1, 100)
            data_item = DataItem.DataItem(d)
            document_model.append_data_item(data_item)
            computation = Symbolic.Computation()
            computation.create_object("a", document_model.get_object_specifier(data_item, "data"))
            computation.parse_expression(document_model, "a[2:2, :, :]", dict())
            self.assertIsNone(computation.evaluate())

    def test_ability_to_take_slice_with_ellipses_produces_correct_data(self):
        document_model = DocumentModel.DocumentModel()
        with contextlib.closing(document_model):
            d = numpy.zeros((4, 8, 8), dtype=numpy.uint32)
            d[:] = random.randint(1, 100)
            data_item = DataItem.DataItem(d)
            document_model.append_data_item(data_item)
            computation = Symbolic.Computation()
            computation.create_object("a", document_model.get_object_specifier(data_item, "data"))
            computation.parse_expression(document_model, "a[2, ...]", dict())
            data = computation.evaluate().data
            assert numpy.array_equal(data, d[2, ...])

    def test_ability_to_take_slice_with_ellipses_produces_correct_calibration(self):
        document_model = DocumentModel.DocumentModel()
        with contextlib.closing(document_model):
            d = numpy.zeros((4, 8, 8), dtype=numpy.uint32)
            d[:] = random.randint(1, 100)
            data_item = DataItem.DataItem(d)
            data_item.maybe_data_source.set_dimensional_calibrations([Calibration.Calibration(10, 20, "m"), Calibration.Calibration(11, 21, "mm"), Calibration.Calibration(12, 22, "nm")])
            document_model.append_data_item(data_item)
            computation = Symbolic.Computation()
            computation.create_object("a", document_model.get_object_specifier(data_item, "data"))
            computation.parse_expression(document_model, "a[2, ...]", dict())
            data_and_metadata = computation.evaluate()
            self.assertEqual(len(data_and_metadata.data_shape), len(data_and_metadata.dimensional_calibrations))
            self.assertEqual("mm", data_and_metadata.dimensional_calibrations[0].units)
            self.assertEqual("nm", data_and_metadata.dimensional_calibrations[1].units)

    def test_ability_to_take_slice_with_newaxis(self):
        document_model = DocumentModel.DocumentModel()
        with contextlib.closing(document_model):
            d = numpy.zeros((8, 8), dtype=numpy.uint32)
            d[:] = random.randint(1, 100)
            data_item = DataItem.DataItem(d)
            document_model.append_data_item(data_item)
            computation = Symbolic.Computation()
            computation.create_object("a", document_model.get_object_specifier(data_item, "data"))
            computation.parse_expression(document_model, "a[newaxis, ...]", dict())
            data = computation.evaluate().data
            assert numpy.array_equal(data, d[numpy.newaxis, ...])

    def test_slice_sum_sums_correct_slices(self):
        document_model = DocumentModel.DocumentModel()
        with contextlib.closing(document_model):
            d = numpy.random.randn(16, 4, 4)
            data_item = DataItem.DataItem(d)
            document_model.append_data_item(data_item)
            computation = Symbolic.Computation()
            computation.create_object("a", document_model.get_object_specifier(data_item, "data"))
            computation.parse_expression(document_model, "slice_sum(a, 4, 6)", dict())
            data = computation.evaluate().data
            assert numpy.array_equal(data, numpy.sum(d[1:7, ...], 0))

    def test_reshape_1d_to_2d_produces_correct_data(self):
        document_model = DocumentModel.DocumentModel()
        with contextlib.closing(document_model):
            d = numpy.random.randn(4)
            data_item = DataItem.DataItem(d)
            document_model.append_data_item(data_item)
            computation = Symbolic.Computation()
            computation.create_object("a", document_model.get_object_specifier(data_item, "data"))
            computation.parse_expression(document_model, "reshape(a, shape(2, 2))", dict())
            data = computation.evaluate().data
            assert numpy.array_equal(data, numpy.reshape(d, (2, 2)))
            computation = Symbolic.Computation()
            computation.create_object("a", document_model.get_object_specifier(data_item, "data"))
            computation.parse_expression(document_model, "reshape(a, shape(4, -1))", dict())
            data = computation.evaluate().data
            assert numpy.array_equal(data, numpy.reshape(d, (4, -1)))
            computation = Symbolic.Computation()
            computation.create_object("a", document_model.get_object_specifier(data_item, "data"))
            computation.parse_expression(document_model, "reshape(a, shape(-1, 4))", dict())
            data = computation.evaluate().data
            assert numpy.array_equal(data, numpy.reshape(d, (-1, 4)))

    def test_reshape_1d_to_2d_preserves_calibration(self):
        document_model = DocumentModel.DocumentModel()
        with contextlib.closing(document_model):
            d = numpy.random.randn(4)
            data_item = DataItem.DataItem(d)
            data_item.maybe_data_source.set_dimensional_calibrations([Calibration.Calibration(1.1, 2.1, "m")])
            document_model.append_data_item(data_item)
            computation = Symbolic.Computation()
            computation.create_object("a", document_model.get_object_specifier(data_item, "data"))
            expression = "reshape(a, shape(4, -1))"
            computation.parse_expression(document_model, expression, dict())
            data_and_metadata = computation.evaluate()
            self.assertEqual("m", data_and_metadata.dimensional_calibrations[0].units)
            self.assertEqual("", data_and_metadata.dimensional_calibrations[1].units)
            computation = Symbolic.Computation()
            computation.create_object("a", document_model.get_object_specifier(data_item, "data"))
            expression = "reshape(a, shape(-1, 4))"
            computation.parse_expression(document_model, expression, dict())
            data_and_metadata = computation.evaluate()
            self.assertEqual("", data_and_metadata.dimensional_calibrations[0].units)
            self.assertEqual("m", data_and_metadata.dimensional_calibrations[1].units)

    def test_reshape_2d_n_x_1_to_1d_preserves_calibration(self):
        document_model = DocumentModel.DocumentModel()
        with contextlib.closing(document_model):
            d = numpy.random.randn(4, 1)
            data_item = DataItem.DataItem(d)
            data_item.maybe_data_source.set_dimensional_calibrations([Calibration.Calibration(1.1, 2.1, "m"), Calibration.Calibration()])
            document_model.append_data_item(data_item)
            computation = Symbolic.Computation()
            computation.create_object("a", document_model.get_object_specifier(data_item, "data"))
            expression = "reshape(a, shape(4))"
            computation.parse_expression(document_model, expression, dict())
            data_and_metadata = computation.evaluate()
            self.assertEqual(1, len(data_and_metadata.dimensional_calibrations))
            self.assertEqual("m", data_and_metadata.dimensional_calibrations[0].units)

    def test_reshape_to_match_another_item(self):
        document_model = DocumentModel.DocumentModel()
        with contextlib.closing(document_model):
            d = numpy.random.randn(4)
            d2 = numpy.random.randn(2, 2)
            data_item = DataItem.DataItem(d)
            document_model.append_data_item(data_item)
            data_item2 = DataItem.DataItem(d2)
            document_model.append_data_item(data_item2)
            computation = Symbolic.Computation()
            computation.create_object("a", document_model.get_object_specifier(data_item, "data"))
            computation.create_object("b", document_model.get_object_specifier(data_item2, "data"))
            computation.parse_expression(document_model, "reshape(a, data_shape(b))", dict())
            data = computation.evaluate().data
            assert numpy.array_equal(data, numpy.reshape(d, (2, 2)))

    def test_concatenate_two_images(self):
        document_model = DocumentModel.DocumentModel()
        with contextlib.closing(document_model):
            d = numpy.random.randn(4, 4)
            data_item = DataItem.DataItem(d)
            document_model.append_data_item(data_item)
            computation = Symbolic.Computation()
            computation.create_object("a", document_model.get_object_specifier(data_item, "data"))
            computation.parse_expression(document_model, "concatenate((a[0:2, 0:2], a[2:4, 2:4]))", dict())
            data = computation.evaluate().data
            assert numpy.array_equal(data, numpy.concatenate((d[0:2, 0:2], d[2:4, 2:4])))

    def test_concatenate_keeps_calibrations_in_non_axis_dimensions(self):
        document_model = DocumentModel.DocumentModel()
        with contextlib.closing(document_model):
            d = numpy.random.randn(4, 4)
            data_item = DataItem.DataItem(d)
            data_item.maybe_data_source.set_intensity_calibration(Calibration.Calibration(1.0, 2.0, "nm"))
            data_item.maybe_data_source.set_dimensional_calibrations([Calibration.Calibration(1.1, 2.1, "m"), Calibration.Calibration(1.2, 2.2, "s")])
            document_model.append_data_item(data_item)
            computation = Symbolic.Computation()
            computation.create_object("a", document_model.get_object_specifier(data_item, "data"))
            computation.parse_expression(document_model, "concatenate((a[0:2, 0:2], a[2:4, 2:4]))", dict())
            data_and_metadata = computation.evaluate()
            self.assertEqual("nm", data_and_metadata.intensity_calibration.units)
            self.assertEqual("m", data_and_metadata.dimensional_calibrations[0].units)
            self.assertEqual("", data_and_metadata.dimensional_calibrations[1].units)

    def test_concatenate_along_alternate_axis_images(self):
        document_model = DocumentModel.DocumentModel()
        with contextlib.closing(document_model):
            d = numpy.random.randn(4)
            data_item = DataItem.DataItem(d)
            document_model.append_data_item(data_item)
            computation = Symbolic.Computation()
            computation.create_object("a", document_model.get_object_specifier(data_item, "data"))
            computation.parse_expression(document_model, "concatenate((reshape(a, shape(1, -1)), reshape(a, shape(1, -1))), 0)", dict())
            data = computation.evaluate().data
            assert numpy.array_equal(data, numpy.concatenate((numpy.reshape(d, (1, -1)), numpy.reshape(d, (1, -1))), 0))

    def test_concatenate_three_images_along_second_axis(self):
        document_model = DocumentModel.DocumentModel()
        with contextlib.closing(document_model):
            d = numpy.random.randn(4, 4)
            data_item = DataItem.DataItem(d)
            document_model.append_data_item(data_item)
            computation = Symbolic.Computation()
            computation.create_object("a", document_model.get_object_specifier(data_item, "data"))
            computation.parse_expression(document_model, "concatenate((a[0:2, 0:2], a[1:3, 1:3], a[2:4, 2:4]), 1)", dict())
            data = computation.evaluate().data
            assert numpy.array_equal(data, numpy.concatenate((d[0:2, 0:2], d[1:3, 1:3], d[2:4, 2:4]), 1))

    def test_ability_to_write_read_basic_nodes(self):
        document_model = DocumentModel.DocumentModel()
        with contextlib.closing(document_model):
            src_data = numpy.zeros((8, 8), dtype=numpy.uint32)
            src_data[:] = random.randint(1, 100)
            data_item = DataItem.DataItem(src_data)
            document_model.append_data_item(data_item)
            computation = Symbolic.Computation()
            computation.create_object("a", document_model.get_object_specifier(data_item, "data"))
            computation.parse_expression(document_model, "-a / average(a) * 5", dict())
            data_node_dict = computation.write_to_dict()
            computation2 = Symbolic.Computation()
            computation2.read_from_dict(data_node_dict)
            computation2.reparse(document_model, dict())
            data = computation.evaluate().data
            data2 = computation2.evaluate().data
            assert numpy.array_equal(data, -src_data / numpy.average(src_data) * 5)
            assert numpy.array_equal(data, data2)

    def test_make_operation_works_without_exception_and_produces_correct_data(self):
        document_model = DocumentModel.DocumentModel()
        document_controller = DocumentController.DocumentController(self.app.ui, document_model, workspace_id="library")
        with contextlib.closing(document_controller):
            d = numpy.zeros((8, 8), dtype=numpy.uint32)
            d[:] = random.randint(1, 100)
            data_item = DataItem.DataItem(d)
            document_model.append_data_item(data_item)
            computation = Symbolic.Computation()
            computation.create_object("a", document_model.get_object_specifier(data_item, "data"))
            computation.parse_expression(document_model, "-a / average(a) * 5", dict())
            data = computation.evaluate().data
            assert numpy.array_equal(data, -d / numpy.average(d) * 5)

    def test_fft_returns_complex_data(self):
        document_model = DocumentModel.DocumentModel()
        with contextlib.closing(document_model):
            d = numpy.random.randn(64, 64)
            data_item = DataItem.DataItem(d)
            document_model.append_data_item(data_item)
            computation = Symbolic.Computation()
            computation.create_object("a", document_model.get_object_specifier(data_item, "data"))
            computation.parse_expression(document_model, "fft(a)", dict())
            data = computation.evaluate().data
            assert numpy.array_equal(data, scipy.fftpack.fftshift(scipy.fftpack.fft2(d) * 1.0 / numpy.sqrt(d.shape[1] * d.shape[0])))

    def test_gaussian_blur_handles_scalar_argument(self):
        document_model = DocumentModel.DocumentModel()
        with contextlib.closing(document_model):
            d = numpy.random.randn(64, 64)
            data_item = DataItem.DataItem(d)
            document_model.append_data_item(data_item)
            computation = Symbolic.Computation()
            computation.create_object("a", document_model.get_object_specifier(data_item, "data"))
            computation.parse_expression(document_model, "gaussian_blur(a, 4.0)", dict())
            data = computation.evaluate().data
            assert numpy.array_equal(data, scipy.ndimage.gaussian_filter(d, sigma=4.0))

    def test_transpose_flip_handles_args(self):
        document_model = DocumentModel.DocumentModel()
        with contextlib.closing(document_model):
            d = numpy.random.randn(30, 60)
            data_item = DataItem.DataItem(d)
            document_model.append_data_item(data_item)
            computation = Symbolic.Computation()
            computation.create_object("a", document_model.get_object_specifier(data_item, "data"))
            computation.parse_expression(document_model, "transpose_flip(a, flip_v=True)", dict())
            data = computation.evaluate().data
            assert numpy.array_equal(data, numpy.flipud(d))

    def test_crop_handles_args(self):
        document_model = DocumentModel.DocumentModel()
        with contextlib.closing(document_model):
            d = numpy.random.randn(64, 64)
            data_item = DataItem.DataItem(d)
            region = Region.RectRegion()
            region.center = 0.41, 0.51
            region.size = 0.52, 0.42
            data_item.maybe_data_source.add_region(region)
            document_model.append_data_item(data_item)
            computation = Symbolic.Computation()
            computation.create_object("a", document_model.get_object_specifier(data_item, "data"))
            computation.create_object("regionA", document_model.get_object_specifier(region))
            computation.parse_expression(document_model, "crop(a, regionA.bounds)", dict())
            data = computation.evaluate().data
            assert numpy.array_equal(data, d[9:42, 19:45])

    def test_evaluate_computation_within_document_model_gives_correct_value(self):
        document_model = DocumentModel.DocumentModel()
        with contextlib.closing(document_model):
            data = numpy.ones((2, 2), numpy.double)
            data_item = DataItem.DataItem(data)
            document_model.append_data_item(data_item)
            computation = Symbolic.Computation()
            computation.create_object("a", document_model.get_object_specifier(data_item, "data"))
            computation.parse_expression(document_model, "-a", dict())
            data_and_metadata = computation.evaluate()
            self.assertTrue(numpy.array_equal(data_and_metadata.data, -data))

    def test_computation_within_document_model_fires_needs_update_event_when_data_changes(self):
        document_model = DocumentModel.DocumentModel()
        with contextlib.closing(document_model):
            data = numpy.ones((2, 2), numpy.double)
            data_item = DataItem.DataItem(data)
            document_model.append_data_item(data_item)
            computation = Symbolic.Computation()
            computation.create_object("a", document_model.get_object_specifier(data_item, "data"))
            computation.parse_expression(document_model, "-a", dict())
            needs_update_ref = [False]
            def needs_update():
                needs_update_ref[0] = True
            needs_update_event_listener = computation.needs_update_event.listen(needs_update)
            with contextlib.closing(needs_update_event_listener):
                with data_item.maybe_data_source.data_ref() as dr:
                    dr.data += 1.5
            self.assertTrue(needs_update_ref[0])

    def test_computation_within_document_model_fires_needs_update_event_when_metadata_changes(self):
        document_model = DocumentModel.DocumentModel()
        with contextlib.closing(document_model):
            data = numpy.ones((2, 2), numpy.double)
            data_item = DataItem.DataItem(data)
            document_model.append_data_item(data_item)
            computation = Symbolic.Computation()
            computation.create_object("a", document_model.get_object_specifier(data_item, "data"))
            computation.parse_expression(document_model, "-a", dict())
            needs_update_ref = [False]
            def needs_update():
                needs_update_ref[0] = True
            needs_update_event_listener = computation.needs_update_event.listen(needs_update)
            with contextlib.closing(needs_update_event_listener):
                metadata = data_item.maybe_data_source.metadata
                metadata["abc"] = 1
                data_item.maybe_data_source.set_metadata(metadata)
            self.assertTrue(needs_update_ref[0])

    def test_computation_within_document_model_fires_needs_update_event_when_object_property(self):
        document_model = DocumentModel.DocumentModel()
        with contextlib.closing(document_model):
            data = numpy.random.randn(64, 64)
            data_item = DataItem.DataItem(data)
            region = Region.RectRegion()
            region.center = 0.41, 0.51
            region.size = 0.52, 0.42
            data_item.maybe_data_source.add_region(region)
            document_model.append_data_item(data_item)
            computation = Symbolic.Computation()
            computation.create_object("a", document_model.get_object_specifier(data_item, "data"))
            computation.create_object("regionA", document_model.get_object_specifier(region))
            computation.parse_expression(document_model, "crop(a, regionA.bounds)", dict())
            needs_update_ref = [False]
            def needs_update():
                needs_update_ref[0] = True
            needs_update_event_listener = computation.needs_update_event.listen(needs_update)
            with contextlib.closing(needs_update_event_listener):
                data_item.maybe_data_source.regions[0].size = 0.53, 0.43
            self.assertTrue(needs_update_ref[0])

    def test_computation_handles_data_lookups(self):
        document_model = DocumentModel.DocumentModel()
        document_controller = DocumentController.DocumentController(self.app.ui, document_model, workspace_id="library")
        with contextlib.closing(document_controller):
            d = numpy.random.randn(2, 2)
            data_item = DataItem.DataItem(d)
            document_model.append_data_item(data_item)
            computation = Symbolic.Computation()
            computation.parse_expression(document_model, "-data_by_uuid(uuid.UUID('{}'))".format(str(data_item.uuid)), dict())
            data_and_metadata = computation.evaluate()
            assert numpy.array_equal(data_and_metadata.data, -d)

    def test_computation_handles_region_lookups(self):
        document_model = DocumentModel.DocumentModel()
        document_controller = DocumentController.DocumentController(self.app.ui, document_model, workspace_id="library")
        with contextlib.closing(document_controller):
            d = numpy.random.randn(100, 100)
            data_item = DataItem.DataItem(d)
            region = Region.RectRegion()
            region.center = 0.5, 0.5
            region.size = 0.6, 0.4
            data_item.maybe_data_source.add_region(region)
            document_model.append_data_item(data_item)
            computation = Symbolic.Computation()
            computation.create_object("a", document_model.get_object_specifier(data_item, "data"))
            computation.parse_expression(document_model, "crop(a, region_by_uuid(uuid.UUID('{}')).bounds)".format(str(region.uuid)), dict())
            data_and_metadata = computation.evaluate()
            assert numpy.array_equal(data_and_metadata.data, d[20:80, 30:70])

    def test_computation_copies_metadata_during_computation(self):
        document_model = DocumentModel.DocumentModel()
        document_controller = DocumentController.DocumentController(self.app.ui, document_model, workspace_id="library")
        with contextlib.closing(document_controller):
            d = numpy.zeros((8, 8), dtype=numpy.uint32)
            d[:] = random.randint(1, 100)
            data_item = DataItem.DataItem(d)
            data_item.maybe_data_source.set_metadata({"abc": 1})
            data_item.maybe_data_source.set_intensity_calibration(Calibration.Calibration(1.0, 2.0, "nm"))
            data_item.maybe_data_source.set_dimensional_calibrations([Calibration.Calibration(1.1, 2.1, "m"), Calibration.Calibration(1.2, 2.2, "m")])
            document_model.append_data_item(data_item)
            computation = Symbolic.Computation()
            computation.create_object("a", document_model.get_object_specifier(data_item, "data"))
            computation.parse_expression(document_model, "-a / average(a) * 5", dict())
            data_and_metadata = computation.evaluate()
            self.assertEqual(data_and_metadata.metadata, data_item.maybe_data_source.metadata)
            self.assertEqual(data_and_metadata.intensity_calibration, data_item.maybe_data_source.intensity_calibration)
            self.assertEqual(data_and_metadata.dimensional_calibrations, data_item.maybe_data_source.dimensional_calibrations)

    def test_remove_data_item_with_computation_succeeds(self):
        document_model = DocumentModel.DocumentModel()
        document_controller = DocumentController.DocumentController(self.app.ui, document_model, workspace_id="library")
        with contextlib.closing(document_controller):
            d = numpy.ones((8, 8), dtype=numpy.uint32)
            data_item = DataItem.DataItem(d)
            document_model.append_data_item(data_item)
            map = {"a": document_model.get_object_specifier(data_item, "data")}
            new_data_item = document_controller.processing_computation("-a", map)
            document_model.recompute_all()
            document_model.remove_data_item(new_data_item)

    def test_evaluate_corrupt_computation_within_document_model_gives_sensible_response(self):
        document_model = DocumentModel.DocumentModel()
        with contextlib.closing(document_model):
            data = numpy.ones((2, 2), numpy.double)
            data_item = DataItem.DataItem(data)
            document_model.append_data_item(data_item)
            computation = Symbolic.Computation()
            computation.create_object("a", document_model.get_object_specifier(data_item, "data"))
            computation.parse_expression(document_model, "(a++)", dict())
            data_and_metadata = computation.evaluate()
            self.assertIsNone(data_and_metadata)

    def test_evaluate_computation_with_invalid_source_gives_sensible_response(self):
        document_model = DocumentModel.DocumentModel()
        with contextlib.closing(document_model):
            data = numpy.ones((2, 2), numpy.double)
            data_item = DataItem.DataItem(data)
            document_model.append_data_item(data_item)
            computation = Symbolic.Computation()
            computation.create_object("a", document_model.get_object_specifier(data_item, "data"))
            computation.parse_expression(document_model, "a+e", dict())
            data_and_metadata = computation.evaluate()
            self.assertIsNone(data_and_metadata)

    def test_evaluate_computation_with_invalid_function_in_document_fails_cleanly(self):
        document_model = DocumentModel.DocumentModel()
        document_controller = DocumentController.DocumentController(self.app.ui, document_model, workspace_id="library")
        with contextlib.closing(document_controller):
            data = numpy.ones((2, 2), numpy.double)
            data_item = DataItem.DataItem(data)
            document_model.append_data_item(data_item)
            map = {"a": document_model.get_object_specifier(data_item, "data")}
            document_controller.processing_computation("void(a,2)", map)
            document_model.recompute_all()

    def test_computation_changed_updates_evaluated_data(self):
        document_model = DocumentModel.DocumentModel()
        with contextlib.closing(document_model):
            data = numpy.ones((2, 2), numpy.double)
            data_item = DataItem.DataItem(data)
            document_model.append_data_item(data_item)
            computation = Symbolic.Computation()
            computation.create_object("a", document_model.get_object_specifier(data_item, "data"))
            computation.parse_expression(document_model, "-a", dict())
            data_and_metadata = computation.evaluate()
            self.assertTrue(numpy.array_equal(data_and_metadata.data, -data))
            computation.parse_expression(document_model, "-2 * a", dict())
            data_and_metadata = computation.evaluate()
            self.assertTrue(numpy.array_equal(data_and_metadata.data, -data*2))

    def test_changing_computation_updates_data_item(self):
        document_model = DocumentModel.DocumentModel()
        document_controller = DocumentController.DocumentController(self.app.ui, document_model, workspace_id="library")
        with contextlib.closing(document_controller):
            data = numpy.random.randn(2, 2)
            data_item = DataItem.DataItem(data)
            document_model.append_data_item(data_item)
            map = {"a": document_model.get_object_specifier(data_item)}
            document_controller.processing_computation("-a.data", map)
            document_model.recompute_all()
            computed_data_item = document_model.data_items[1]
            self.assertTrue(numpy.array_equal(computed_data_item.maybe_data_source.data, -data))
            computed_data_item.maybe_data_source.computation.parse_expression(document_model, "-a.data * 2", dict())
            document_model.recompute_all()
            self.assertTrue(numpy.array_equal(computed_data_item.maybe_data_source.data, -data * 2))

    def test_unary_functions_return_correct_dimensions(self):
        document_model = DocumentModel.DocumentModel()
        with contextlib.closing(document_model):
            data = numpy.random.randn(2, 2)
            data_item = DataItem.DataItem(data)
            document_model.append_data_item(data_item)
            computation = Symbolic.Computation()
            computation.create_object("a", document_model.get_object_specifier(data_item, "data"))
            computation.parse_expression(document_model, "sin(a)", dict())
            data_and_metadata = computation.evaluate()
            self.assertEqual(len(data_and_metadata.dimensional_calibrations), 2)

    def test_computation_stores_original_text(self):
        document_model = DocumentModel.DocumentModel()
        with contextlib.closing(document_model):
            data = numpy.random.randn(2, 2)
            data_item = DataItem.DataItem(data)
            document_model.append_data_item(data_item)
            computation = Symbolic.Computation()
            computation.create_object("a", document_model.get_object_specifier(data_item, "data"))
            computation.parse_expression(document_model, "sin(a)", dict())
            self.assertEqual(computation.original_expression, "sin(a)")

    def test_computation_stores_error_and_original_text(self):
        document_model = DocumentModel.DocumentModel()
        with contextlib.closing(document_model):
            data = numpy.random.randn(2, 2)
            data_item = DataItem.DataItem(data)
            document_model.append_data_item(data_item)
            computation = Symbolic.Computation()
            computation.create_object("a", document_model.get_object_specifier(data_item, "data"))
            computation.parse_expression(document_model, "xyz(a)", dict())
            data_and_metadata = computation.evaluate()
            self.assertIsNone(data_and_metadata)
            self.assertTrue(computation.error_text is not None and len(computation.error_text) > 0)
            self.assertEqual(computation.original_expression, "xyz(a)")

    def test_computation_reloads_missing_scalar_function(self):
        document_model = DocumentModel.DocumentModel()
        with contextlib.closing(document_model):
            src_data = numpy.zeros((8, 8), dtype=numpy.uint32)
            src_data[:] = random.randint(0, 100)
            data_item = DataItem.DataItem(src_data)
            document_model.append_data_item(data_item)
            computation = Symbolic.Computation()
            computation.create_object("a", document_model.get_object_specifier(data_item, "data"))
            computation.parse_expression(document_model, "average(a)", dict())
            data_node_dict = computation.write_to_dict()
            data_node_dict['original_expression'] = 'missing(a)'
            computation2 = Symbolic.Computation()
            computation2.read_from_dict(data_node_dict)
            computation2.reparse(document_model, dict())
            self.assertIsNone(computation2.evaluate())

    def test_computation_can_extract_item_from_scalar_tuple(self):
        document_model = DocumentModel.DocumentModel()
        with contextlib.closing(document_model):
            data = ((numpy.random.randn(4, 2) + 1) * 10).astype(numpy.uint32)
            data_item = DataItem.DataItem(data)
            document_model.append_data_item(data_item)
            computation = Symbolic.Computation()
            computation.create_object("a", document_model.get_object_specifier(data_item, "data"))
            computation.parse_expression(document_model, "a + data_shape(a)[1] + data_shape(a)[0]", dict())
            data_and_metadata = computation.evaluate()
            self.assertTrue(numpy.array_equal(data_and_metadata.data, data + 6))

    def test_columns_and_rows_and_radius_functions_return_correct_values(self):
        document_model = DocumentModel.DocumentModel()
        with contextlib.closing(document_model):
            data = ((numpy.random.randn(10, 8) + 1) * 10).astype(numpy.uint32)
            data_item = DataItem.DataItem(data)
            document_model.append_data_item(data_item)
            computation = Symbolic.Computation()
            computation.create_object("a", document_model.get_object_specifier(data_item, "data"))
            computation.parse_expression(document_model, "row(a, -1, 1) + column(a, -1, 1) + radius(a)", dict())
            data_and_metadata = computation.evaluate()
            icol, irow = numpy.meshgrid(numpy.linspace(-1, 1, 8), numpy.linspace(-1, 1, 10))
            self.assertTrue(numpy.array_equal(data_and_metadata.data, icol + irow + numpy.sqrt(pow(icol, 2) + pow(irow, 2))))

    def test_copying_data_item_with_computation_copies_computation(self):
        document_model = DocumentModel.DocumentModel()
        with contextlib.closing(document_model):
            data = ((numpy.random.randn(10, 8) + 1) * 10).astype(numpy.uint32)
            data_item = DataItem.DataItem(data)
            document_model.append_data_item(data_item)
            computation = Symbolic.Computation()
            computation.create_object("a", document_model.get_object_specifier(data_item, "data"))
            computed_data_item = DataItem.DataItem(data.copy())
            computation.parse_expression(document_model, "-a", dict())
            computed_data_item.maybe_data_source.set_computation(computation)
            document_model.append_data_item(computed_data_item)
            document_model.recompute_all()
            copied_data_item = copy.deepcopy(computed_data_item)
            document_model.append_data_item(copied_data_item)
            self.assertIsNotNone(copied_data_item.maybe_data_source.computation)
            self.assertEqual(computed_data_item.maybe_data_source.computation.error_text, copied_data_item.maybe_data_source.computation.error_text)
            self.assertEqual(computed_data_item.maybe_data_source.computation.original_expression, copied_data_item.maybe_data_source.computation.original_expression)

    def test_changing_computation_source_data_updates_computation(self):
        document_model = DocumentModel.DocumentModel()
        with contextlib.closing(document_model):
            data = ((numpy.random.randn(10, 8) + 1) * 10).astype(numpy.uint32)
            data_item = DataItem.DataItem(data)
            document_model.append_data_item(data_item)
            computation = Symbolic.Computation()
            computation.create_object("a", document_model.get_object_specifier(data_item, "data"))
            computed_data_item = DataItem.DataItem(data.copy())
            computation.parse_expression(document_model, "-a", dict())
            computed_data_item.maybe_data_source.set_computation(computation)
            document_model.append_data_item(computed_data_item)
            computation.needs_update_event.fire()  # ugh. bootstrap.
            document_model.recompute_all()
            self.assertTrue(numpy.array_equal(data_item.maybe_data_source.data, data))
            self.assertTrue(numpy.array_equal(computed_data_item.maybe_data_source.data, -data_item.maybe_data_source.data))
            with data_item.maybe_data_source.data_ref() as dr:
                dr.data = ((numpy.random.randn(10, 8) + 1) * 10).astype(numpy.uint32)
            document_model.recompute_all()
            self.assertFalse(numpy.array_equal(data_item.maybe_data_source.data, data))
            self.assertTrue(numpy.array_equal(computed_data_item.maybe_data_source.data, -data_item.maybe_data_source.data))

    def test_computation_is_live_after_copying_data_item_with_computation(self):
        document_model = DocumentModel.DocumentModel()
        with contextlib.closing(document_model):
            data = ((numpy.random.randn(10, 8) + 1) * 10).astype(numpy.int32)
            data_item = DataItem.DataItem(data)
            document_model.append_data_item(data_item)
            computation = Symbolic.Computation()
            computation.create_object("a", document_model.get_object_specifier(data_item, "data"))
            computed_data_item = DataItem.DataItem(data.copy())
            computation.parse_expression(document_model, "-a", dict())
            computed_data_item.maybe_data_source.set_computation(computation)
            document_model.append_data_item(computed_data_item)
            computation.needs_update_event.fire()  # ugh. bootstrap.
            document_model.recompute_all()
            self.assertTrue(numpy.array_equal(computed_data_item.maybe_data_source.data, -data_item.maybe_data_source.data))
            copied_data_item = copy.deepcopy(computed_data_item)
            document_model.append_data_item(copied_data_item)
            with data_item.maybe_data_source.data_ref() as dr:
                dr.data = ((numpy.random.randn(10, 8) + 1) * 10).astype(numpy.int32)
            copied_data_item.maybe_data_source.computation.needs_update_event.fire()  # ugh. bootstrap.
            print("NEEDS EVAL")
            document_model.recompute_all()
            print(data, computed_data_item.maybe_data_source.data, -data_item.maybe_data_source.data)
            self.assertTrue(numpy.array_equal(computed_data_item.maybe_data_source.data, -data_item.maybe_data_source.data))
            self.assertTrue(numpy.array_equal(copied_data_item.maybe_data_source.data, -data_item.maybe_data_source.data))

    def test_computation_extracts_data_property_of_data_item(self):
        document_model = DocumentModel.DocumentModel()
        with contextlib.closing(document_model):
            data = ((numpy.random.randn(10, 8) + 1) * 10).astype(numpy.uint32)
            data_item = DataItem.DataItem(data)
            document_model.append_data_item(data_item)
            computation = Symbolic.Computation()
            computation.create_object("a", document_model.get_object_specifier(data_item))
            computed_data_item = DataItem.DataItem(data.copy())
            computation.parse_expression(document_model, "a.data", dict())
            computed_data_item.maybe_data_source.set_computation(computation)
            document_model.append_data_item(computed_data_item)
            computation.needs_update_event.fire()  # ugh. bootstrap.
            document_model.recompute_all()
            self.assertTrue(numpy.array_equal(computed_data_item.maybe_data_source.data, data_item.maybe_data_source.data))

    def test_resample_produces_correct_data(self):
        document_model = DocumentModel.DocumentModel()
        with contextlib.closing(document_model):
            data = ((numpy.abs(numpy.random.randn(10, 8)) + 1) * 10).astype(numpy.uint32)
            data_item = DataItem.DataItem(data)
            document_model.append_data_item(data_item)
            computation = Symbolic.Computation()
            computation.create_object("a", document_model.get_object_specifier(data_item, "data"))
            computed_data_item = DataItem.DataItem(data.copy())
            computation.parse_expression(document_model, "resample_image(a, shape(5, 4))", dict())
            computed_data_item.maybe_data_source.set_computation(computation)
            document_model.append_data_item(computed_data_item)
            computation.needs_update_event.fire()  # ugh. bootstrap.
            document_model.recompute_all()
            self.assertTrue(numpy.array_equal(computed_data_item.maybe_data_source.data, Image.scaled(data_item.maybe_data_source.data, (5, 4))))

    def test_resample_with_data_shape_produces_correct_data(self):
        document_model = DocumentModel.DocumentModel()
        with contextlib.closing(document_model):
            data = ((numpy.abs(numpy.random.randn(10, 8)) + 1) * 10).astype(numpy.uint32)
            data_item = DataItem.DataItem(data)
            document_model.append_data_item(data_item)
            data2 = numpy.zeros((5, 4), numpy.uint32)
            data_item2 = DataItem.DataItem(data2)
            document_model.append_data_item(data_item2)
            computation = Symbolic.Computation()
            computation.create_object("a", document_model.get_object_specifier(data_item, "data"))
            computation.create_object("b", document_model.get_object_specifier(data_item2, "data"))
            computed_data_item = DataItem.DataItem(data.copy())
            computation.parse_expression(document_model, "resample_image(a, data_shape(b))", dict())
            computed_data_item.maybe_data_source.set_computation(computation)
            document_model.append_data_item(computed_data_item)
            computation.needs_update_event.fire()  # ugh. bootstrap.
            document_model.recompute_all()
            self.assertTrue(numpy.array_equal(computed_data_item.maybe_data_source.data, Image.scaled(data_item.maybe_data_source.data, (5, 4))))

    def test_computation_extracts_display_data_property_of_data_item(self):
        document_model = DocumentModel.DocumentModel()
        with contextlib.closing(document_model):
            src_data = ((numpy.random.randn(10, 8) + 1) * 10).astype(numpy.uint32)
            data_item = DataItem.DataItem(src_data)
            document_model.append_data_item(data_item)
            computation = Symbolic.Computation()
            computation.create_object("a", document_model.get_object_specifier(data_item))
            computation.parse_expression(document_model, "a.display_data", dict())
            data_node_dict = computation.write_to_dict()
            computation2 = Symbolic.Computation()
            computation2.read_from_dict(data_node_dict)
            computation2.reparse(document_model, dict())
            data = computation.evaluate().data
            data2 = computation2.evaluate().data
            assert numpy.array_equal(data, src_data)
            assert numpy.array_equal(data, data2)

    def test_evaluation_with_variable_produces_correct_data(self):
        document_model = DocumentModel.DocumentModel()
        document_controller = DocumentController.DocumentController(self.app.ui, document_model, workspace_id="library")
        with contextlib.closing(document_controller):
            d = numpy.random.randn(2, 2)
            data_item = DataItem.DataItem(d)
            document_model.append_data_item(data_item)
            computation = Symbolic.Computation()
            computation.create_variable("x", value_type="integral", value=5)
            computation.create_object("a", document_model.get_object_specifier(data_item, "data"))
            computation.parse_expression(document_model, "a + x", dict())
            data = computation.evaluate().data
            assert numpy.array_equal(data, d + 5)

    def test_evaluation_with_two_variables_produces_correct_data(self):
        document_model = DocumentModel.DocumentModel()
        document_controller = DocumentController.DocumentController(self.app.ui, document_model, workspace_id="library")
        with contextlib.closing(document_controller):
            src_data = ((numpy.abs(numpy.random.randn(10, 8)) + 1) * 10).astype(numpy.uint32)
            data_item = DataItem.DataItem(src_data)
            document_model.append_data_item(data_item)
            computation = Symbolic.Computation()
            computation.create_variable("x", value_type="integral", value=5)
            computation.create_variable("y", value_type="integral", value=5)
            computation.create_object("a", document_model.get_object_specifier(data_item, "data"))
            computation.parse_expression(document_model, "gaussian_blur(a, x - y)", dict())
            assert numpy.array_equal(computation.evaluate().data, src_data)

    def test_changing_variable_value_updates_computation(self):
        document_model = DocumentModel.DocumentModel()
        document_controller = DocumentController.DocumentController(self.app.ui, document_model, workspace_id="library")
        with contextlib.closing(document_controller):
            src_data = numpy.random.randn(2, 2)
            data_item = DataItem.DataItem(src_data)
            document_model.append_data_item(data_item)
            computation = Symbolic.Computation()
            x = computation.create_variable("x", value_type="integral", value=5)
            computation.create_object("a", document_model.get_object_specifier(data_item, "data"))
            computation.parse_expression(document_model, "a + x", dict())
            computed_data_item = DataItem.DataItem(src_data.copy())
            computed_data_item.maybe_data_source.set_computation(computation)
            document_model.append_data_item(computed_data_item)
            computation.needs_update_event.fire()  # ugh. bootstrap.
            document_model.recompute_all()
            self.assertTrue(numpy.array_equal(computed_data_item.maybe_data_source.data, src_data + 5))
            x.value = 8
            document_model.recompute_all()
            self.assertTrue(numpy.array_equal(computed_data_item.maybe_data_source.data, src_data + 8))

    def test_changing_variable_name_has_no_effect_on_computation(self):
        document_model = DocumentModel.DocumentModel()
        document_controller = DocumentController.DocumentController(self.app.ui, document_model, workspace_id="library")
        with contextlib.closing(document_controller):
            src_data = numpy.random.randn(2, 2)
            data_item = DataItem.DataItem(src_data)
            document_model.append_data_item(data_item)
            computation = Symbolic.Computation()
            x = computation.create_variable("x", value_type="integral", value=5)
            computation.create_object("a", document_model.get_object_specifier(data_item, "data"))
            computation.parse_expression(document_model, "a + x", dict())
            computed_data_item = DataItem.DataItem(src_data.copy())
            computed_data_item.maybe_data_source.set_computation(computation)
            document_model.append_data_item(computed_data_item)
            computation.needs_update_event.fire()  # ugh. bootstrap.
            document_model.recompute_all()
            self.assertTrue(numpy.array_equal(computed_data_item.maybe_data_source.data, src_data + 5))
            x.name = "xx"
            document_model.recompute_all()
            self.assertTrue(numpy.array_equal(computed_data_item.maybe_data_source.data, src_data + 5))

    def test_computation_with_variable_reloads(self):
        document_model = DocumentModel.DocumentModel()
        with contextlib.closing(document_model):
            src_data = ((numpy.abs(numpy.random.randn(10, 8)) + 1) * 10).astype(numpy.uint32)
            data_item = DataItem.DataItem(src_data)
            document_model.append_data_item(data_item)
            computation = Symbolic.Computation()
            computation.create_variable("x", value_type="integral", value=5)
            computation.create_object("a", document_model.get_object_specifier(data_item, "data"))
            computation.parse_expression(document_model, "a + x", dict())
            d = computation.write_to_dict()
            computation2 = Symbolic.Computation()
            computation2.read_from_dict(d)
            computation2.reparse(document_model, dict())
            self.assertTrue(numpy.array_equal(computation.evaluate().data, src_data + 5))
            self.assertTrue(numpy.array_equal(computation2.evaluate().data, src_data + 5))

    def test_computation_variable_writes_and_reads(self):
        variable = Symbolic.ComputationVariable("x", value_type="integral", value=5)
        self.assertEqual(variable.name, "x")
        self.assertEqual(variable.value, 5)
        data_node_dict = variable.write_to_dict()
        variable2 = Symbolic.ComputationVariable()
        variable2.read_from_dict(data_node_dict)
        self.assertEqual(variable.name, variable2.name)
        self.assertEqual(variable.value, variable2.value)

    def test_computation_reparsing_keeps_variables(self):
        document_model = DocumentModel.DocumentModel()
        with contextlib.closing(document_model):
            src_data = ((numpy.random.randn(10, 8) + 1) * 10).astype(numpy.uint32)
            data_item = DataItem.DataItem(src_data)
            document_model.append_data_item(data_item)
            computation = Symbolic.Computation()
            x = computation.create_variable("x", value_type="integral", value=5)
            computation.create_object("a", document_model.get_object_specifier(data_item, "data"))
            computation.parse_expression(document_model, "a + x", dict())
            self.assertTrue(numpy.array_equal(computation.evaluate().data, src_data + 5))
            computation.parse_expression(document_model, "x + a", dict())
            self.assertTrue(numpy.array_equal(computation.evaluate().data, src_data + 5))

    def test_computation_using_object_parses_and_evaluates(self):
        document_model = DocumentModel.DocumentModel()
        with contextlib.closing(document_model):
            src_data = ((numpy.random.randn(10, 8) + 1) * 10).astype(numpy.uint32)
            data_item = DataItem.DataItem(src_data)
            document_model.append_data_item(data_item)
            computation = Symbolic.Computation()
            computation.create_variable("x", value_type="integral", value=5)
            computation.create_object("a", document_model.get_object_specifier(data_item, "data"))
            computation.parse_expression(document_model, "a + x", dict())
            self.assertTrue(numpy.array_equal(computation.evaluate().data, src_data + 5))

    def test_computation_using_object_updates_when_data_changes(self):
        document_model = DocumentModel.DocumentModel()
        with contextlib.closing(document_model):
            src_data = ((numpy.random.randn(10, 8) + 1) * 10).astype(numpy.uint32)
            data_item = DataItem.DataItem(src_data)
            document_model.append_data_item(data_item)
            computation = Symbolic.Computation()
            computation.create_variable("x", value_type="integral", value=5)
            computation.create_object("a", document_model.get_object_specifier(data_item, "data"))
            computation.parse_expression(document_model, "a + x", dict())
            self.assertTrue(numpy.array_equal(computation.evaluate().data, src_data + 5))
            d = computation.write_to_dict()
            read_computation = Symbolic.Computation()
            read_computation.read_from_dict(d)
            read_computation.reparse(document_model, dict())
            src_data2 = ((numpy.random.randn(10, 8) + 1) * 10).astype(numpy.uint32)
            with data_item.maybe_data_source.data_ref() as dr:
                dr.data = src_data2
            self.assertTrue(numpy.array_equal(read_computation.evaluate().data, src_data2 + 5))

    def test_computation_using_object_updates_efficiently_when_region_changes(self):
        document_model = DocumentModel.DocumentModel()
        with contextlib.closing(document_model):
            src_data = ((numpy.abs(numpy.random.randn(12, 8)) + 1) * 10).astype(numpy.uint32)
            data_item = DataItem.DataItem(src_data)
            region = Region.RectRegion()
            region.bounds = Geometry.FloatRect.from_center_and_size(Geometry.FloatPoint(0.5, 0.5), Geometry.FloatSize(0.5, 0.5))
            data_item.maybe_data_source.add_region(region)
            document_model.append_data_item(data_item)
            computation = Symbolic.Computation()
            computation.create_object("a", document_model.get_object_specifier(data_item, "data"))
            computation.create_object("r", document_model.get_object_specifier(region))
            computation.parse_expression(document_model, "crop(a, r.bounds)", dict())
            computed_data_item = DataItem.DataItem(src_data.copy())
            computed_data_item.maybe_data_source.set_computation(computation)
            document_model.append_data_item(computed_data_item)
            computation.needs_update_event.fire()  # ugh. bootstrap.
            document_model.recompute_all()
            self.assertTrue(numpy.array_equal(computed_data_item.maybe_data_source.data, src_data[3:9, 2:6]))
            region.bounds = Geometry.FloatRect.from_center_and_size(Geometry.FloatPoint(0.25, 0.25), Geometry.FloatSize(0.5, 0.5))
            region.bounds = Geometry.FloatRect.from_center_and_size(Geometry.FloatPoint(0.0, 0.0), Geometry.FloatSize(0.5, 0.5))
            region.bounds = Geometry.FloatRect.from_center_and_size(Geometry.FloatPoint(0.25, 0.25), Geometry.FloatSize(0.5, 0.5))
            evaluation_count = computation._evaluation_count_for_test
            document_model.recompute_all()
            self.assertEqual(computation._evaluation_count_for_test - evaluation_count, 1)
            self.assertTrue(numpy.array_equal(computed_data_item.maybe_data_source.data, src_data[0:6, 0:4]))

    def test_computation_with_object_writes_and_reads(self):
        document_model = DocumentModel.DocumentModel()
        with contextlib.closing(document_model):
            src_data = ((numpy.random.randn(10, 8) + 1) * 10).astype(numpy.uint32)
            data_item = DataItem.DataItem(src_data)
            document_model.append_data_item(data_item)
            computation = Symbolic.Computation()
            a_specifier = document_model.get_object_specifier(data_item)
            computation.create_object("a", document_model.get_object_specifier(data_item, "data"))
            computation.parse_expression(document_model, "a + 4", dict())
            d = computation.write_to_dict()
            read_computation = Symbolic.Computation()
            read_computation.read_from_dict(d)
            read_computation.reparse(document_model, dict())
            self.assertEqual(read_computation.variables[0].name, "a")
            print(read_computation.variables[0].specifier, a_specifier)
            self.assertEqual(read_computation.variables[0].specifier, a_specifier)

    def test_computation_with_object_reloads(self):
        document_model = DocumentModel.DocumentModel()
        with contextlib.closing(document_model):
            src_data = ((numpy.random.randn(10, 8) + 1) * 10).astype(numpy.uint32)
            data_item = DataItem.DataItem(src_data)
            document_model.append_data_item(data_item)
            computation = Symbolic.Computation()
            computation.create_variable("x", value_type="integral", value=5)
            computation.create_object("a", document_model.get_object_specifier(data_item, "data"))
            computation.parse_expression(document_model, "a + x", dict())
            d = computation.write_to_dict()
            computation2 = Symbolic.Computation()
            computation2.read_from_dict(d)
            computation2.reparse(document_model, dict())
            self.assertTrue(numpy.array_equal(computation.evaluate().data, src_data + 5))
            self.assertTrue(numpy.array_equal(computation2.evaluate().data, src_data + 5))

    def test_computation_with_object_evaluates_correctly_after_changing_the_variable_name(self):
        document_model = DocumentModel.DocumentModel()
        with contextlib.closing(document_model):
            src_data = ((numpy.random.randn(10, 8) + 1) * 10).astype(numpy.uint32)
            data_item = DataItem.DataItem(src_data)
            document_model.append_data_item(data_item)
            computation = Symbolic.Computation()
            computation.create_object("a", document_model.get_object_specifier(data_item, "data"))
            x = computation.create_variable("x", value_type="integral", value=5)
            computation.parse_expression(document_model, "a + x", dict())
            self.assertTrue(numpy.array_equal(computation.evaluate().data, src_data + 5))
            x.name = "xx"
            computation.parse_expression(document_model, "a + xx", dict())
            self.assertTrue(numpy.array_equal(computation.evaluate().data, src_data + 5))

    def test_computation_with_object_evaluates_correctly_after_changing_the_specifier(self):
        document_model = DocumentModel.DocumentModel()
        with contextlib.closing(document_model):
            src_data1 = ((numpy.random.randn(10, 8) + 1) * 10).astype(numpy.uint32)
            src_data2 = ((numpy.random.randn(10, 8) + 1) * 10).astype(numpy.uint32)
            data_item1 = DataItem.DataItem(src_data1)
            data_item2 = DataItem.DataItem(src_data2)
            document_model.append_data_item(data_item1)
            document_model.append_data_item(data_item2)
            computation = Symbolic.Computation()
            a = computation.create_object("a", document_model.get_object_specifier(data_item1, "data"))
            expression = "a + 1"
            computation.parse_expression(document_model, expression, dict())
            self.assertTrue(numpy.array_equal(computation.evaluate().data, src_data1 + 1))
            a.specifier = document_model.get_object_specifier(data_item2)
            computation.parse_expression(document_model, expression, dict())
            self.assertTrue(numpy.array_equal(computation.evaluate().data, src_data2 + 1))

    def test_computation_fires_needs_update_event_when_specifier_changes(self):
        document_model = DocumentModel.DocumentModel()
        with contextlib.closing(document_model):
            src_data1 = ((numpy.random.randn(10, 8) + 1) * 10).astype(numpy.uint32)
            src_data2 = ((numpy.random.randn(10, 8) + 1) * 10).astype(numpy.uint32)
            data_item1 = DataItem.DataItem(src_data1)
            data_item2 = DataItem.DataItem(src_data2)
            document_model.append_data_item(data_item1)
            document_model.append_data_item(data_item2)
            computation = Symbolic.Computation()
            a = computation.create_object("a", document_model.get_object_specifier(data_item1, "data"))
            expression = "a + 1"
            computation.parse_expression(document_model, expression, dict())
            needs_update_ref = [False]
            def needs_update():
                needs_update_ref[0] = True
            needs_update_event_listener = computation.needs_update_event.listen(needs_update)
            with contextlib.closing(needs_update_event_listener):
                a.specifier = document_model.get_object_specifier(data_item2)
            self.assertTrue(needs_update_ref[0])

    def test_computation_in_document_recomputes_when_specifier_changes(self):
        document_model = DocumentModel.DocumentModel()
        with contextlib.closing(document_model):
            src_data1 = ((numpy.random.randn(10, 8) + 1) * 10).astype(numpy.uint32)
            src_data2 = ((numpy.random.randn(10, 8) + 1) * 10).astype(numpy.uint32)
            data_item1 = DataItem.DataItem(src_data1)
            data_item2 = DataItem.DataItem(src_data2)
            document_model.append_data_item(data_item1)
            document_model.append_data_item(data_item2)
            computation = Symbolic.Computation()
            a = computation.create_object("a", document_model.get_object_specifier(data_item1, "data"))
            expression = "a + 1"
            computation.parse_expression(document_model, expression, dict())
            computed_data_item = DataItem.DataItem(src_data1.copy())
            computed_data_item.maybe_data_source.set_computation(computation)
            document_model.append_data_item(computed_data_item)
            computation.needs_update_event.fire()  # ugh. bootstrap.
            document_model.recompute_all()
            self.assertTrue(numpy.array_equal(computed_data_item.maybe_data_source.data, src_data1 + 1))
            a.specifier = document_model.get_object_specifier(data_item2)
            document_model.recompute_all()
            self.assertTrue(numpy.array_equal(computed_data_item.maybe_data_source.data, src_data2 + 1))

    def test_computation_with_raw_reference_node_reloads(self):
        document_model = DocumentModel.DocumentModel()
        with contextlib.closing(document_model):
            src_data = ((numpy.random.randn(10, 8) + 1) * 10).astype(numpy.uint32)
            data_item = DataItem.DataItem(src_data)
            document_model.append_data_item(data_item)
            computation = Symbolic.Computation()
            computation.create_variable("x", value_type="integral", value=5)
            a_specifier = document_model.get_object_specifier(data_item, "data")
            computation.create_object("a", a_specifier)
            computation.parse_expression(document_model, "a + x", dict())
            self.assertIsNone(computation.evaluate())
            d = computation.write_to_dict()
            computation2 = Symbolic.Computation()
            computation2.read_from_dict(d)
            computation2.reparse(document_model, dict())
            self.assertIsNone(computation2.evaluate())

    def test_computation_with_raw_reference_copies(self):
        document_model = DocumentModel.DocumentModel()
        with contextlib.closing(document_model):
            src_data = ((numpy.random.randn(10, 8) + 1) * 10).astype(numpy.uint32)
            data_item = DataItem.DataItem(src_data)
            region = Region.RectRegion()
            data_item.maybe_data_source.add_region(region)
            document_model.append_data_item(data_item)
            computation = Symbolic.Computation()
            computation.create_variable("x", value_type="integral", value=5)
            a = computation.create_object("a", document_model.get_object_specifier(data_item, "data"))
            computation.parse_expression(document_model, "a + x", dict())
            computation.remove_variable(a)
            copy.deepcopy(computation)

    def test_evaluation_error_recovers_gracefully(self):
        document_model = DocumentModel.DocumentModel()
        with contextlib.closing(document_model):
            src_data = ((numpy.abs(numpy.random.randn(12, 8)) + 1) * 10).astype(numpy.uint32)
            data_item = DataItem.DataItem(src_data)
            document_model.append_data_item(data_item)
            computation = Symbolic.Computation()
            x = computation.create_variable("x", value_type="integral", value=0)
            computation.create_object("a", document_model.get_object_specifier(data_item, "data"))
            computation.parse_expression(document_model, "line_profile(a, vector(normalized_point(0.25, 0.25), normalized_point(0.5, 0.5)), x)", dict())
            computed_data_item = DataItem.DataItem(src_data.copy())
            computed_data_item.maybe_data_source.set_computation(computation)
            document_model.append_data_item(computed_data_item)
            computation.needs_update_event.fire()  # ugh. bootstrap.
            document_model.recompute_all()
            self.assertIsNotNone(computation.error_text)
            self.assertEqual(len(computed_data_item.maybe_data_source.data.shape), 2)  # original data
            x.value = 1
            document_model.recompute_all()
            self.assertIsNone(computation.error_text)
            self.assertIsNotNone(computed_data_item.maybe_data_source.data)
            self.assertEqual(len(computed_data_item.maybe_data_source.data.shape), 1)  # computed data

    def test_various_expressions_produces_data(self):
        document_model = DocumentModel.DocumentModel()
        with contextlib.closing(document_model):
            src_data = ((numpy.abs(numpy.random.randn(10, 8)) + 1) * 10).astype(numpy.uint32)
            data_item = DataItem.DataItem(src_data)
            document_model.append_data_item(data_item)
            script_and_data = [
                ("histogram(a, 10)", None),
                ("line_profile(a, vector(normalized_point(0.1, 0.1), normalized_point(0.8, 0.7)), 10)", None),
                ("transpose_flip(a, False, True, False)", None),
                ("crop(a, rectangle_from_origin_size(normalized_point(0, 0), normalized_size(0.5, 0.625)))", src_data[0:5, 0:5]),
                ("project(a)", numpy.sum(src_data, 0)),
                ("resample_image(a, shape(32, 32))", Image.scaled(src_data, (32, 32))),
                ("resample_image(a, data_shape(a))", src_data),
                ("resample_image(a, data_shape(crop(a, rectangle_from_origin_size(normalized_point(0, 0), normalized_size(0.5, 0.625)))))", Image.scaled(src_data, (5, 5))),
                ("a + x", src_data + 5),
                ("gaussian_blur(a, x + x)", None),
                ("gaussian_blur(a, x - 2)", None),
                ("gaussian_blur(a, 2 * x)", None),
                ("gaussian_blur(a, +x)", None),
            ]
            for script, data in script_and_data:
                computation = Symbolic.Computation()
                computation.create_object("a", document_model.get_object_specifier(data_item, "data"))
                computation.create_variable("x", value_type="integral", value=5)
                computation.parse_expression(document_model, script, dict())
                computed_data_item = DataItem.DataItem(src_data.copy())
                computed_data_item.maybe_data_source.set_computation(computation)
                document_model.append_data_item(computed_data_item)
                computation.needs_update_event.fire()  # ugh. bootstrap.
                document_model.recompute_all()
                self.assertIsNotNone(computed_data_item.maybe_data_source.data)
                if data is not None:
                    self.assertTrue(numpy.array_equal(computed_data_item.maybe_data_source.data, data))

    def test_conversion_to_int(self):
        document_model = DocumentModel.DocumentModel()
        with contextlib.closing(document_model):
            src_data = ((numpy.abs(numpy.random.randn(10, 8)) + 1) * 10).astype(numpy.float64)
            data_item = DataItem.DataItem(src_data)
            document_model.append_data_item(data_item)
            computation = Symbolic.Computation()
            computation.create_object("src", document_model.get_object_specifier(data_item, "data"))
            computation.parse_expression(document_model, "astype(src, int)", dict())
            data = computation.evaluate().data
            self.assertEqual(data.dtype, numpy.int_)
            self.assertTrue(numpy.array_equal(data, src_data.astype(int)))
            computation.parse_expression(document_model, "astype(src, int16)", dict())
            data = computation.evaluate().data
            self.assertEqual(data.dtype, numpy.int16)
            self.assertTrue(numpy.array_equal(data, src_data.astype(numpy.int16)))
            computation.parse_expression(document_model, "astype(src, int32)", dict())
            data = computation.evaluate().data
            self.assertEqual(data.dtype, numpy.int32)
            self.assertTrue(numpy.array_equal(data, src_data.astype(numpy.int32)))
            computation.parse_expression(document_model, "astype(src, int64)", dict())
            data = computation.evaluate().data
            self.assertEqual(data.dtype, numpy.int64)
            self.assertTrue(numpy.array_equal(data, src_data.astype(numpy.int64)))

    def test_conversion_to_uint(self):
        document_model = DocumentModel.DocumentModel()
        with contextlib.closing(document_model):
            src_data = ((numpy.abs(numpy.random.randn(10, 8)) + 1) * 10).astype(numpy.float64)
            data_item = DataItem.DataItem(src_data)
            document_model.append_data_item(data_item)
            computation = Symbolic.Computation()
            computation.create_object("src", document_model.get_object_specifier(data_item, "data"))
            computation.parse_expression(document_model, "astype(src, uint8)", dict())
            data = computation.evaluate().data
            self.assertEqual(data.dtype, numpy.uint8)
            self.assertTrue(numpy.array_equal(data, src_data.astype(numpy.uint8)))
            computation.parse_expression(document_model, "astype(src, uint16)", dict())
            data = computation.evaluate().data
            self.assertEqual(data.dtype, numpy.uint16)
            self.assertTrue(numpy.array_equal(data, src_data.astype(numpy.uint16)))
            computation.parse_expression(document_model, "astype(src, uint32)", dict())
            data = computation.evaluate().data
            self.assertEqual(data.dtype, numpy.uint32)
            self.assertTrue(numpy.array_equal(data, src_data.astype(numpy.uint32)))
            computation.parse_expression(document_model, "astype(src, uint64)", dict())
            data = computation.evaluate().data
            self.assertEqual(data.dtype, numpy.uint64)
            self.assertTrue(numpy.array_equal(data, src_data.astype(numpy.uint64)))

    def test_conversion_to_float(self):
        document_model = DocumentModel.DocumentModel()
        with contextlib.closing(document_model):
            src_data = ((numpy.abs(numpy.random.randn(10, 8)) + 1) * 10).astype(numpy.int32)
            data_item = DataItem.DataItem(src_data)
            document_model.append_data_item(data_item)
            computation = Symbolic.Computation()
            computation.create_object("src", document_model.get_object_specifier(data_item, "data"))
            computation.parse_expression(document_model, "astype(src, float32)", dict())
            data = computation.evaluate().data
            self.assertEqual(data.dtype, numpy.float32)
            self.assertTrue(numpy.array_equal(data, src_data.astype(numpy.float32)))
            computation.parse_expression(document_model, "astype(src, float64)", dict())
            data = computation.evaluate().data
            self.assertEqual(data.dtype, numpy.float64)
            self.assertTrue(numpy.array_equal(data, src_data.astype(numpy.float64)))

    def test_conversion_to_complex(self):
        document_model = DocumentModel.DocumentModel()
        with contextlib.closing(document_model):
            src_data = ((numpy.abs(numpy.random.randn(10, 8)) + 1) * 10).astype(numpy.int32)
            data_item = DataItem.DataItem(src_data)
            document_model.append_data_item(data_item)
            computation = Symbolic.Computation()
            computation.create_object("src", document_model.get_object_specifier(data_item, "data"))
            computation.parse_expression(document_model, "astype(src, complex64)", dict())
            data = computation.evaluate().data
            self.assertEqual(data.dtype, numpy.complex64)
            self.assertTrue(numpy.array_equal(data, src_data.astype(numpy.complex64)))
            computation.parse_expression(document_model, "astype(src, complex128)", dict())
            data = computation.evaluate().data
            self.assertEqual(data.dtype, numpy.complex128)
            self.assertTrue(numpy.array_equal(data, src_data.astype(numpy.complex128)))

    def disabled_test_delete_source_region_of_computation_deletes_target_data_item(self):
        document_model = DocumentModel.DocumentModel()
        document_controller = DocumentController.DocumentController(self.app.ui, document_model, workspace_id="library")
        with contextlib.closing(document_controller):
            source_data_item = DataItem.DataItem(numpy.ones((8, 8), numpy.float32))
            document_model.append_data_item(source_data_item)
            target_data_item = document_controller.get_line_profile_new(source_data_item)
            display = DataItem.DisplaySpecifier.from_data_item(source_data_item).display
            self.assertIn(target_data_item, document_model.data_items)
            display.remove_drawn_graphic(display.drawn_graphics[0])
            self.assertNotIn(target_data_item, document_model.data_items)

    def disabled_test_reshape_rgb(self):
        assert False

    def disabled_test_computation_with_data_error_gets_reported(self):
        assert False  # when the data node returns None

    def disabled_test_computation_variable_gets_closed(self):
        assert False

    def disabled_test_computation_with_cycles_fails_gracefully(self):
        assert False

    def disabled_test_computations_handle_constant_values_as_errors(self):
        # computation.parse_expression(document_model, "7", dict())
        assert False

    def disabled_test_computations_update_data_item_dependencies_list(self):
        assert False

    def disabled_test_function_to_modify_intensity_calibration(self):
        assert False

    def disabled_test_function_to_modify_dimensional_calibrations(self):
        assert False

    def disabled_test_function_to_modify_metadata(self):
        assert False

    def test_data_slice_calibration_with_step(self):
        # d[::2, :, :]
        pass

    def disabled_test_invalid_computation_produces_error_message(self):
        # example d[3:3, ...]
        # should return None be allowed? what about raise exception in all cases?
        pass

if __name__ == '__main__':
    logging.getLogger().setLevel(logging.DEBUG)
    unittest.main()
