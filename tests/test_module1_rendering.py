import unittest
import numpy as np
from ai.runtime.sonar_rendering import scale_samples


class RenderingTests(unittest.TestCase):
    def test_low_amplitude_uint16_data_remains_visible(self):
        raw=np.tile(np.arange(1,401,dtype=np.uint16),(128,1));raw[:,0]=0
        gray,metadata=scale_samples(raw)
        self.assertGreater(np.median(gray),100)
        self.assertGreater(np.std(gray),25)
        self.assertTrue(np.all(gray[:,0]==0))
        self.assertEqual(metadata['version'],'LOG1P_PERCENTILE_V1')
        self.assertEqual(metadata['detector_validation'],'UNVALIDATED_RENDERING_DOMAIN')

    def test_outliers_do_not_flatten_normal_returns(self):
        raw=np.tile(np.arange(1,101,dtype=np.uint16),(128,1));raw[0,0]=65535
        gray,_=scale_samples(raw)
        self.assertGreater(np.median(gray),100);self.assertGreater(np.std(gray),25)

    def test_empty_and_constant_rows_are_not_invented(self):
        self.assertTrue(np.all(scale_samples(np.zeros((16,64),dtype=np.uint16))[0]==0))
        self.assertEqual(len(np.unique(scale_samples(np.full((16,64),25,dtype=np.uint16))[0])),1)
        for bad in [np.array([[float('nan')]]),np.array([[-1]]),np.array([1,2,3])]:
            with self.assertRaises(ValueError):scale_samples(bad)

if __name__=='__main__':unittest.main()
