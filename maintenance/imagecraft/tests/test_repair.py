from copy import deepcopy
import hashlib
from importlib import import_module
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / 'imagecraft/scripts'))
mod = import_module('repair_image')
Image = import_module('PIL.Image')
ImageDraw = import_module('PIL.ImageDraw')


class RasterRepair(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.source = self.root / 'source.png'
        im = Image.new('RGB', (128, 96), 'white')
        ImageDraw.Draw(im).rectangle((34, 24, 44, 32), fill='black')
        im.save(self.source)
        self.original = self.source.read_bytes()
        self.spec = {'schema': 'imagecraft.raster-repair/1', 'source_sha256': hashlib.sha256(self.original).hexdigest(),
                     'size': [128, 96], 'masks': [{'rect': [30, 20, 50, 40]}], 'texts': [], 'paths': []}
        self.output = self.root / 'result'

    def test_inpaint_preserves_every_outside_pixel_and_source(self):
        receipt = mod.repair(self.source, self.spec, self.output)
        self.assertEqual(self.original, self.source.read_bytes())
        self.assertEqual(receipt['changes_outside_erasure_or_overlay'], 0)
        self.assertGreater(receipt['changed_pixels'], 0)
        with Image.open(self.source) as a, Image.open(self.output/'image.png') as b:
            for y in range(96):
                for x in range(128):
                    if not (30 <= x < 50 and 20 <= y < 40):
                        self.assertEqual(a.getpixel((x,y)), b.getpixel((x,y)))
        self.assertEqual(receipt['state'], 'repaired_visual_and_semantic_review_required')

    def test_wrong_hash_or_size_rejected_before_output(self):
        for key, value in [('source_sha256', '0'*64), ('size', [64, 96])]:
            spec = deepcopy(self.spec); spec[key] = value
            with self.assertRaises(ValueError):
                mod.repair(self.source, spec, self.output)
            self.assertFalse(self.output.exists())

    def test_no_overwrite(self):
        self.output.mkdir()
        sentinel = self.output/'image.png'; sentinel.write_bytes(b'keep')
        with self.assertRaises(ValueError):
            mod.repair(self.source, self.spec, self.output)
        self.assertEqual(sentinel.read_bytes(), b'keep')

    def test_invalid_rectangles_and_large_erasure_rejected(self):
        for rect in [[-1,0,5,5], [0,0,129,20], [5,5,5,10], [True,0,5,5], [0,0,128,96]]:
            spec = deepcopy(self.spec); spec['masks'] = [{'rect':rect}]
            with self.subTest(rect=rect), self.assertRaises(ValueError):
                mod.repair(self.source, spec, self.output)
            self.assertFalse(self.output.exists())

    def test_invalid_spec_and_empty_operations_rejected(self):
        for spec in [[], {'schema':'wrong'}, {**self.spec,'masks':[]}, {**self.spec,'masks':[None]}]:
            with self.subTest(spec=spec), self.assertRaises(ValueError):
                mod.repair(self.source, spec, self.output)
            self.assertFalse(self.output.exists())

    def test_path_overlay_does_not_require_opencv(self):
        spec = deepcopy(self.spec); spec['masks'] = []
        spec['paths'] = [{'points':[[20,70],[100,70]],'width':3,'color':'#FF0000','arrow':True}]
        def existing_modules(name):
            if name == 'cv2':
                raise ImportError('not installed')
            return import_module(name)
        with patch.object(mod, 'import_module', side_effect=existing_modules):
            receipt = mod.repair(self.source, spec, self.output)
        self.assertIsNone(receipt['opencv_version'])
        self.assertEqual(receipt['changes_outside_erasure_or_overlay'], 0)
        with Image.open(self.output/'image.png') as result:
            self.assertNotEqual(result.getpixel((90,70)), (255,255,255))
            self.assertEqual(result.getpixel((0,0)), (255,255,255))

    def test_erasure_reports_missing_optional_opencv(self):
        def existing_modules(name):
            if name == 'cv2':
                raise ImportError('not installed')
            return import_module(name)
        with patch.object(mod, 'import_module', side_effect=existing_modules), self.assertRaisesRegex(ValueError, 'OpenCV'):
            mod.repair(self.source, self.spec, self.output)
        self.assertFalse(self.output.exists())

    def test_bad_connectors_rejected(self):
        base = {'points':[[20,70],[100,70]],'width':3,'color':'#FF0000','arrow':True}
        for update in [{'points':[[20,70],[20,70]]}, {'arrow':'false'}, {'points':[[20,70],[23,70]]},
                       {'points':[[0,0],[100,70]]}, {'color':'red'}, {'width':True}]:
            spec=deepcopy(self.spec); spec['masks']=[]; spec['paths']=[{**base,**update}]
            with self.subTest(update=update), self.assertRaises(ValueError):
                mod.repair(self.source,spec,self.output)
            self.assertFalse(self.output.exists())

    def test_text_fit_and_overflow(self):
        font = next((p for p in [Path('C:/Windows/Fonts/arial.ttf'),Path('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf')] if p.is_file()),None)
        if font is None:
            self.skipTest('No fixture font installed; do not download fonts for tests')
        spec=deepcopy(self.spec); spec['masks']=[]
        text={'text':'FIX','box':[10,50,90,85],'font_size':18,'font_file':str(font),'color':'#112233'}
        spec['texts']=[text]
        receipt=mod.repair(self.source,spec,self.output)
        self.assertEqual(receipt['texts'][0]['text'],'FIX')
        self.assertTrue(receipt['texts'][0]['fits'])
        spec['texts']=[{**text,'text':'THIS DOES NOT FIT','box':[10,50,20,60]}]
        with self.assertRaisesRegex(ValueError,'fit'):
            mod.repair(self.source,spec,self.root/'overflow')
        self.assertFalse((self.root/'overflow').exists())

    def test_bit_depth_and_color_profiles_require_explicit_normalization(self):
        for mode, options in [('L', {}), ('RGB', {'icc_profile': b'test-profile'})]:
            Image.new(mode, (128,96)).save(self.source, **options)
            self.spec['source_sha256']=hashlib.sha256(self.source.read_bytes()).hexdigest()
            with self.subTest(mode=mode), self.assertRaises(ValueError):
                mod.repair(self.source,self.spec,self.output)
            self.assertFalse(self.output.exists())

    def test_transparency_rejected(self):
        im=Image.new('RGBA',(128,96),(255,255,255,0)); im.save(self.source)
        self.spec['source_sha256']=hashlib.sha256(self.source.read_bytes()).hexdigest()
        with self.assertRaisesRegex(ValueError,'Transparent'):
            mod.repair(self.source,self.spec,self.output)
        self.assertFalse(self.output.exists())


if __name__ == '__main__':
    unittest.main()
