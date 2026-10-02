import unittest
import numpy as np
from ai.runtime.xtf import windows
class XTFWindowTests(unittest.TestCase):
    def test_bounded_channels_and_source_lineage(self):
        def records():
            for i in range(35):yield dict(channel=i%2,samples=np.array([0,65535],dtype=np.uint16),ping_number=i,packet_offset=1024+i*64)
        result=list(windows(records(),rows=16))
        self.assertEqual(sum(len(ref['ping_numbers']) for _,ref in result),35)
        for image,ref in result:
            self.assertLessEqual(image.shape[0],16)
            self.assertEqual(image[0].tolist(),[0,255])
            self.assertEqual(ref['navigation_status'],'UNVERIFIED_UNITS_DATUM_POSE')
    def test_binary_packet_framing_and_no_pickle_index(self):
        import ctypes,tempfile
        from pathlib import Path
        try: import pyxtf
        except ImportError: self.skipTest('Optional pyxtf not installed.')
        from ai.runtime.xtf import packets
        header=pyxtf.XTFFileHeader();header.NumberOfSonarChannels=1
        info=pyxtf.XTFChanInfo();info.TypeOfChannel=1;info.BytesPerSample=2;info.SampleFormat=3;header.ChanInfo[0]=info
        ping=pyxtf.XTFPingHeader();ping.NumChansToFollow=1;ping.PingNumber=7
        channel=pyxtf.XTFPingChanHeader();channel.ChannelNumber=0;channel.NumSamples=4;channel.SlantRange=50
        samples=np.array([0,100,200,65535],dtype=np.uint16).tobytes()
        ping.NumBytesThisRecord=ctypes.sizeof(ping)+ctypes.sizeof(channel)+len(samples)
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'test.xtf';path.write_bytes(bytes(header)+bytes(ping)+bytes(channel)+samples)
            path.with_suffix('.pyxtf_idx').write_bytes(b'NOT_A_PICKLE_DO_NOT_LOAD')
            parsed=list(packets(path));self.assertEqual(parsed[0]['ping_number'],7)
            self.assertEqual(parsed[0]['samples'].tolist(),[0,100,200,65535])
            self.assertEqual(parsed[0]['timestamp_raw'],None)
            self.assertEqual(parsed[0]['timestamp_timezone'],'UNVERIFIED')
            self.assertEqual(parsed[0]['channel_type_raw'],1)
            path.write_bytes(path.read_bytes()[:-1])
            with self.assertRaises(ValueError):list(packets(path))
    def test_limits(self):
        with self.assertRaises(ValueError):list(windows([],rows=10000))
if __name__=='__main__':unittest.main()
