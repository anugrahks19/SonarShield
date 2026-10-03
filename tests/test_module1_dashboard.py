import base64,json,tempfile,threading,unittest,http.client,time
from pathlib import Path
from http.server import ThreadingHTTPServer
from ai.runtime.survey_dashboard import SurveyService,handler,MAX_UPLOAD


class DashboardTests(unittest.TestCase):
    def test_limits_do_not_start_or_queue_analysis(self):
        with tempfile.TemporaryDirectory() as folder:
            calls=[];service=SurveyService(folder,runner=lambda *a,**kw:calls.append(kw))
            for size,settings in [(MAX_UPLOAD+1,{}),(1024,{'max_windows':101}),(1024,{'device':'cuda'}),(1024,{'rows':16,'overlap':16}),(1024,{'rows':True})]:
                with self.assertRaises(ValueError):service.reserve(size,settings)
            job,file=service.reserve(1024,{})
            with self.assertRaises(RuntimeError):service.reserve(1024,{})
            self.assertFalse(calls);service.failed_upload(job);self.assertIsNone(service.active)

    def test_binary_upload_origin_checks_and_result_path_isolation(self):
        with tempfile.TemporaryDirectory() as folder:
            calls=[];done=threading.Event()
            def runner(log,output,**kw):
                calls.append((Path(log).read_bytes(),kw));output.mkdir();(output/'index.html').write_text('TEST ONLY');done.set();return dict(status='BOUNDED_COMPLETE',windows_completed=1)
            service=SurveyService(folder,runner=runner);server=ThreadingHTTPServer(('127.0.0.1',0),handler(service,0));port=server.server_address[1];server.RequestHandlerClass=handler(service,port)
            threading.Thread(target=server.serve_forever,daemon=True).start()
            def request(path,body=b'',headers=None,method='POST'):
                connection=http.client.HTTPConnection('127.0.0.1',port,timeout=5);connection.request(method,path,body=body,headers=headers or {});r=connection.getresponse();data=r.read();connection.close();return r.status,data
            try:
                body=bytes([123])+bytes(1023);headers={'Origin':f'http://127.0.0.1:{port}','X-Sonar-Session':service.token,'Content-Type':'application/octet-stream','X-Sonar-Options':base64.b64encode(json.dumps({'max_windows':1}).encode()).decode()}
                self.assertEqual(request('/jobs',body,dict(headers,Origin='https://foreign.invalid'))[0],403);self.assertFalse(calls)
                self.assertEqual(request('/jobs',body,dict(headers,**{'X-Sonar-Session':'wrong'}))[0],403)
                self.assertEqual(request('/jobs',body,dict(headers,Host='attacker.invalid'))[0],403)
                status,data=request('/jobs',body,headers);self.assertEqual(status,202);job=json.loads(data)['id'];self.assertTrue(done.wait(2));self.assertEqual(calls[0][0],body);self.assertEqual(calls[0][1]['device'],'cpu')
                self.assertEqual(request(f'/results/{job}/index.html',method='GET')[0],200)
                self.assertEqual(request(f'/results/{job}/../../input.xtf',method='GET')[0],404)
                self.assertEqual(request(f'/results/{job}/input.xtf',method='GET')[0],404)
                self.assertEqual(request('/jobs',method='GET')[0],200)
            finally:server.shutdown();server.server_close()

    def test_invalid_upload_clears_active_job_and_retains_no_bytes(self):
        with tempfile.TemporaryDirectory() as folder:
            service=SurveyService(folder);job,file=service.reserve(1024,{})
            file.write_bytes(b'partial');service.failed_upload(job)
            self.assertFalse(file.exists());self.assertIsNone(service.active);self.assertEqual(service.status(job)['status'],'FAILED')

    def test_restart_restores_jobs_without_starting_inference(self):
        with tempfile.TemporaryDirectory() as folder:
            first=SurveyService(folder);job,file=first.reserve(1024,{})
            file.write_bytes(bytes([123])+bytes(1023))
            results=file.parent/'results';results.mkdir();(results/'job.json').write_text(json.dumps(dict(status='BOUNDED_COMPLETE',windows_completed=4)))
            calls=[];second=SurveyService(folder,runner=lambda *a,**kw:calls.append(kw))
            self.assertEqual(second.status(job)['windows_completed'],4);self.assertEqual(second.status(job)['status'],'BOUNDED_COMPLETE');self.assertIsNone(second.active);self.assertFalse(calls)

    def test_cancel_does_not_promise_interrupting_a_window(self):
        with tempfile.TemporaryDirectory() as folder:
            service=SurveyService(folder);job,file=service.reserve(1024,{})
            result=service.cancel(job);self.assertIn('between windows',result['detail']);self.assertTrue((file.parent/'cancel').exists())

if __name__=='__main__':unittest.main()
