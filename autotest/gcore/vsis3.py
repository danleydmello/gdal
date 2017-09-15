#!/usr/bin/env python
###############################################################################
# $Id$
#
# Project:  GDAL/OGR Test Suite
# Purpose:  Test /vsis3
# Author:   Even Rouault <even dot rouault at spatialys dot com>
#
###############################################################################
# Copyright (c) 2015, Even Rouault <even dot rouault at spatialys dot com>
#
# Permission is hereby granted, free of charge, to any person obtaining a
# copy of this software and associated documentation files (the "Software"),
# to deal in the Software without restriction, including without limitation
# the rights to use, copy, modify, merge, publish, distribute, sublicense,
# and/or sell copies of the Software, and to permit persons to whom the
# Software is furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included
# in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS
# OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL
# THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
# DEALINGS IN THE SOFTWARE.
###############################################################################

import os.path
import sys
from osgeo import gdal

sys.path.append( '../pymod' )

import gdaltest
import webserver

def open_for_read(uri):
    """
    Opens a test file for reading.
    """
    return gdal.VSIFOpenExL(uri, 'rb', 1)

###############################################################################
def vsis3_init():

    gdaltest.aws_vars = {}
    for var in ('AWS_SECRET_ACCESS_KEY', 'AWS_ACCESS_KEY_ID', 'AWS_TIMESTAMP', 'AWS_HTTPS', 'AWS_VIRTUAL_HOSTING', 'AWS_S3_ENDPOINT', 'AWS_REQUEST_PAYER', 'AWS_DEFAULT_REGION', 'AWS_DEFAULT_PROFILE'):
        gdaltest.aws_vars[var] = gdal.GetConfigOption(var)
        if gdaltest.aws_vars[var] is not None:
            gdal.SetConfigOption(var, "")

    # To avoid user AWS credentials in ~/.aws/credentials and ~/.aws/config
    # to mess up our tests
    gdal.SetConfigOption('CPL_AWS_CREDENTIALS_FILE', '')
    gdal.SetConfigOption('AWS_CONFIG_FILE', '')
    gdal.SetConfigOption('CPL_AWS_EC2_CREDENTIALS_URL', '')

    return 'success'

###############################################################################
# Error cases

def vsis3_1():
    try:
        drv = gdal.GetDriverByName( 'HTTP' )
    except:
        drv = None

    if drv is None:
        return 'skip'

        # RETODO: Bind to swig, change test

    # Missing AWS_SECRET_ACCESS_KEY
    gdal.ErrorReset()
    with gdaltest.error_handler():
        f = open_for_read('/vsis3/foo/bar')
    if f is not None or gdal.VSIGetLastErrorMsg().find('AWS_SECRET_ACCESS_KEY') < 0:
        gdaltest.post_reason('fail')
        print(gdal.VSIGetLastErrorMsg())
        return 'fail'

    gdal.ErrorReset()
    with gdaltest.error_handler():
        f = open_for_read('/vsis3_streaming/foo/bar')
    if f is not None or gdal.VSIGetLastErrorMsg().find('AWS_SECRET_ACCESS_KEY') < 0:
        gdaltest.post_reason('fail')
        print(gdal.VSIGetLastErrorMsg())
        return 'fail'

    gdal.SetConfigOption('AWS_SECRET_ACCESS_KEY', 'AWS_SECRET_ACCESS_KEY')

    # Missing AWS_ACCESS_KEY_ID
    gdal.ErrorReset()
    with gdaltest.error_handler():
        f = open_for_read('/vsis3/foo/bar')
    if f is not None or gdal.VSIGetLastErrorMsg().find('AWS_ACCESS_KEY_ID') < 0:
        gdaltest.post_reason('fail')
        print(gdal.VSIGetLastErrorMsg())
        return 'fail'

    gdal.SetConfigOption('AWS_ACCESS_KEY_ID', 'AWS_ACCESS_KEY_ID')

    # ERROR 1: The AWS Access Key Id you provided does not exist in our records.
    gdal.ErrorReset()
    with gdaltest.error_handler():
        f = open_for_read('/vsis3/foo/bar.baz')
    if f is not None or gdal.VSIGetLastErrorMsg() == '':
        if f is not None:
            gdal.VSIFCloseL(f)
        if gdal.GetConfigOption('APPVEYOR') is not None:
            return 'success'
        gdaltest.post_reason('fail')
        print(gdal.VSIGetLastErrorMsg())
        return 'fail'

    gdal.ErrorReset()
    with gdaltest.error_handler():
        f = open_for_read('/vsis3_streaming/foo/bar.baz')
    if f is not None or gdal.VSIGetLastErrorMsg() == '':
        gdaltest.post_reason('fail')
        print(gdal.VSIGetLastErrorMsg())
        return 'fail'

    return 'success'

###############################################################################
def vsis3_start_webserver():

    gdaltest.webserver_process = None
    gdaltest.webserver_port = 0

    try:
        drv = gdal.GetDriverByName( 'HTTP' )
    except:
        drv = None

    if drv is None:
        return 'skip'

    (gdaltest.webserver_process, gdaltest.webserver_port) = webserver.launch(handler = webserver.DispatcherHttpHandler)
    if gdaltest.webserver_port == 0:
        return 'skip'

    gdal.SetConfigOption('AWS_SECRET_ACCESS_KEY', 'AWS_SECRET_ACCESS_KEY')
    gdal.SetConfigOption('AWS_ACCESS_KEY_ID', 'AWS_ACCESS_KEY_ID')
    gdal.SetConfigOption('AWS_TIMESTAMP', '20150101T000000Z')
    gdal.SetConfigOption('AWS_HTTPS', 'NO')
    gdal.SetConfigOption('AWS_VIRTUAL_HOSTING', 'NO')
    gdal.SetConfigOption('AWS_S3_ENDPOINT', '127.0.0.1:%d' % gdaltest.webserver_port)

    return 'success'

def get_s3_fake_bucket_resource_method(request):
    request.protocol_version = 'HTTP/1.1'

    if 'Authorization' not in request.headers:
        sys.stderr.write('Bad headers: %s\n' % str(request.headers))
        request.send_response(403)
        return
    expected_authorization_8080 = 'AWS4-HMAC-SHA256 Credential=AWS_ACCESS_KEY_ID/20150101/us-east-1/s3/aws4_request,SignedHeaders=host;x-amz-content-sha256;x-amz-date,Signature=38901846b865b12ac492bc005bb394ca8d60c098b68db57c084fac686a932f9e'
    expected_authorization_8081 = 'AWS4-HMAC-SHA256 Credential=AWS_ACCESS_KEY_ID/20150101/us-east-1/s3/aws4_request,SignedHeaders=host;x-amz-content-sha256;x-amz-date,Signature=9f623b7ffce76188a456c70fb4813eb31969e88d130d6b4d801b3accbf050d6c'
    if request.headers['Authorization'] != expected_authorization_8080 and request.headers['Authorization'] != expected_authorization_8081:
        sys.stderr.write("Bad Authorization: '%s'\n" % str(request.headers['Authorization']))
        request.send_response(403)
        return

    request.send_response(200)
    request.send_header('Content-type', 'text/plain')
    request.send_header('Content-Length', 3)
    request.end_headers()
    request.wfile.write("""foo""".encode('ascii'))

###############################################################################
# Test with a fake AWS server

def vsis3_2():

    if gdaltest.webserver_port == 0:
        return 'skip'

    handler = webserver.SequentialHandler()
    handler.add('GET', '/s3_fake_bucket/resource', custom_method = get_s3_fake_bucket_resource_method)

    with webserver.install_http_handler(handler):
        f = open_for_read('/vsis3/s3_fake_bucket/resource')
        if f is None:
            gdaltest.post_reason('fail')
            return 'fail'
        data = gdal.VSIFReadL(1, 4, f).decode('ascii')
        gdal.VSIFCloseL(f)

        if data != 'foo':
            gdaltest.post_reason('fail')
            print(data)
            return 'fail'

    handler = webserver.SequentialHandler()
    handler.add('GET', '/s3_fake_bucket/resource', custom_method = get_s3_fake_bucket_resource_method)
    with webserver.install_http_handler(handler):
        f = open_for_read('/vsis3_streaming/s3_fake_bucket/resource')
        if f is None:
            gdaltest.post_reason('fail')
            return 'fail'
        data = gdal.VSIFReadL(1, 4, f).decode('ascii')
        gdal.VSIFCloseL(f)

    if data != 'foo':
        gdaltest.post_reason('fail')
        print(data)
        return 'fail'


    handler = webserver.SequentialHandler()
    def method(request):
        request.protocol_version = 'HTTP/1.1'

        if 'Authorization' not in request.headers:
            sys.stderr.write('Bad headers: %s\n' % str(request.headers))
            request.send_response(403)
            return
        expected_authorization_8080 = 'AWS4-HMAC-SHA256 Credential=AWS_ACCESS_KEY_ID/20150101/us-east-1/s3/aws4_request,SignedHeaders=host;x-amz-content-sha256;x-amz-date;x-amz-security-token,Signature=464a21835038b4f4d292b6463b8a005b9aaa980513aa8c42fc170abb733dce85'
        expected_authorization_8081 = 'AWS4-HMAC-SHA256 Credential=AWS_ACCESS_KEY_ID/20150101/us-east-1/s3/aws4_request,SignedHeaders=host;x-amz-content-sha256;x-amz-date;x-amz-security-token,Signature=b10e91575186342f9f2acfc91c4c2c9938c4a9e8cdcbc043d09d59d9641ad7fb'
        if request.headers['Authorization'] != expected_authorization_8080 and request.headers['Authorization'] != expected_authorization_8081:
            sys.stderr.write("Bad Authorization: '%s'\n" % str(request.headers['Authorization']))
            request.send_response(403)
            return

        request.send_response(200)
        request.send_header('Content-type', 'text/plain')
        request.send_header('Content-Length', 3)
        request.end_headers()
        request.wfile.write("""foo""".encode('ascii'))

    handler.add('GET', '/s3_fake_bucket_with_session_token/resource', custom_method = method)

    # Test with temporary credentials
    with gdaltest.config_option('AWS_SESSION_TOKEN', 'AWS_SESSION_TOKEN'):
        with webserver.install_http_handler(handler):
            f = open_for_read('/vsis3/s3_fake_bucket_with_session_token/resource')
            if f is None:
                gdaltest.post_reason('fail')
                return 'fail'
            data = gdal.VSIFReadL(1, 4, f).decode('ascii')
            gdal.VSIFCloseL(f)

    handler = webserver.SequentialHandler()

    def method(request):
        request.protocol_version = 'HTTP/1.1'
        if 'Range' in request.headers:
            if request.headers['Range'] != 'bytes=0-4095':
                sys.stderr.write("Bad Range: '%s'\n" % str(request.headers['Range']))
                request.send_response(403)
                return
            request.send_response(206)
            request.send_header('Content-type', 'text/plain')
            request.send_header('Content-Range', 'bytes 0-4095/1000000')
            request.send_header('Content-Length', 4096)
            request.end_headers()
            request.wfile.write(''.join('a' for i in range(4096)).encode('ascii'))
        else:
            request.send_response(200)
            request.send_header('Content-type', 'text/plain')
            request.send_header('Content-Length', 1000000)
            request.end_headers()
            request.wfile.write(''.join('a' for i in range(1000000)).encode('ascii'))

    handler.add('GET', '/s3_fake_bucket/resource2.bin', custom_method = method)

    with webserver.install_http_handler(handler):
        #old_val = gdal.GetConfigOption('GDAL_DISABLE_READDIR_ON_OPEN')
        #gdal.SetConfigOption('GDAL_DISABLE_READDIR_ON_OPEN', 'EMPTY_DIR')
        stat_res = gdal.VSIStatL('/vsis3/s3_fake_bucket/resource2.bin')
        #gdal.SetConfigOption('GDAL_DISABLE_READDIR_ON_OPEN', old_val)
        if stat_res is None or stat_res.size != 1000000:
            gdaltest.post_reason('fail')
            if stat_res is not None:
                print(stat_res.size)
            else:
                print(stat_res)
            return 'fail'

    handler = webserver.SequentialHandler()
    handler.add('HEAD', '/s3_fake_bucket/resource2.bin', 200,
                { 'Content-type': 'text/plain',
                  'Content-Length': 1000000 })
    with webserver.install_http_handler(handler):
        stat_res = gdal.VSIStatL('/vsis3_streaming/s3_fake_bucket/resource2.bin')
    if stat_res is None or stat_res.size != 1000000:
        gdaltest.post_reason('fail')
        if stat_res is not None:
            print(stat_res.size)
        else:
            print(stat_res)
        return 'fail'


    handler = webserver.SequentialHandler()

    def method(request):
        request.protocol_version = 'HTTP/1.1'
        if request.headers['Authorization'].find('us-east-1') >= 0:
            request.send_response(400)
            response = '<?xml version="1.0" encoding="UTF-8"?><Error><Message>bla</Message><Code>AuthorizationHeaderMalformed</Code><Region>us-west-2</Region></Error>'
            response = '%x\r\n%s' % (len(response), response)
            request.send_header('Content-type', 'application/xml')
            request.send_header('Transfer-Encoding', 'chunked')
            request.end_headers()
            request.wfile.write(response.encode('ascii'))
        else:
            sys.stderr.write('Bad headers: %s\n' % str(request.headers))
            request.send_response(403)

    handler.add('GET', '/s3_fake_bucket/redirect', custom_method = method)

    def method(request):
        request.protocol_version = 'HTTP/1.1'
        if request.headers['Authorization'].find('us-west-2') >= 0 and request.headers['Host'].startswith('127.0.0.1'):
            request.send_response(301)
            response = '<?xml version="1.0" encoding="UTF-8"?><Error><Message>bla</Message><Code>PermanentRedirect</Code><Endpoint>localhost:%d</Endpoint></Error>' % request.server.port
            response = '%x\r\n%s' % (len(response), response)
            request.send_header('Content-type', 'application/xml')
            request.send_header('Transfer-Encoding', 'chunked')
            request.end_headers()
            request.wfile.write(response.encode('ascii'))
        else:
            sys.stderr.write('Bad headers: %s\n' % str(request.headers))
            request.send_response(403)

    handler.add('GET', '/s3_fake_bucket/redirect', custom_method = method)

    def method(request):
        request.protocol_version = 'HTTP/1.1'
        if request.headers['Authorization'].find('us-west-2') >= 0 and request.headers['Host'].startswith('localhost'):
            request.send_response(200)
            request.send_header('Content-type', 'text/plain')
            request.send_header('Content-Length', 3)
            request.end_headers()
            request.wfile.write("""foo""".encode('ascii'))
        else:
            sys.stderr.write('Bad headers: %s\n' % str(request.headers))
            request.send_response(403)

    handler.add('GET', '/s3_fake_bucket/redirect', custom_method = method)

    # Test region and endpoint 'redirects'
    with webserver.install_http_handler(handler):
        f = open_for_read('/vsis3/s3_fake_bucket/redirect')
        if f is None:
            gdaltest.post_reason('fail')
            return 'fail'
        data = gdal.VSIFReadL(1, 4, f).decode('ascii')
        gdal.VSIFCloseL(f)

    if data != 'foo':

        if gdaltest.is_travis_branch('trusty'):
            print('Skipped on trusty branch, but should be investigated')
            return 'skip'

        gdaltest.post_reason('fail')
        print(data)
        return 'fail'

    # Test region and endpoint 'redirects'
    handler.req_count = 0
    with webserver.install_http_handler(handler):
        f = open_for_read('/vsis3_streaming/s3_fake_bucket/redirect')
        if f is None:
            gdaltest.post_reason('fail')
            return 'fail'
        data = gdal.VSIFReadL(1, 4, f).decode('ascii')
        gdal.VSIFCloseL(f)

    if data != 'foo':
        gdaltest.post_reason('fail')
        print(data)
        return 'fail'


    handler = webserver.SequentialHandler()

    def method(request):
        # /vsis3_streaming/ should have remembered the change of region and endpoint
        if request.headers['Authorization'].find('us-west-2') < 0 or \
            not request.headers['Host'].startswith('localhost'):
            sys.stderr.write('Bad headers: %s\n' % str(request.headers))
            request.send_response(403)

        request.protocol_version = 'HTTP/1.1'
        request.send_response(400)
        response = 'bla'
        response = '%x\r\n%s' % (len(response), response)
        request.send_header('Content-type', 'application/xml')
        request.send_header('Transfer-Encoding', 'chunked')
        request.end_headers()
        request.wfile.write(response.encode('ascii'))

    handler.add('GET', '/s3_fake_bucket/non_xml_error', custom_method = method)

    gdal.ErrorReset()
    with webserver.install_http_handler(handler):
        with gdaltest.error_handler():
            f = open_for_read('/vsis3_streaming/s3_fake_bucket/non_xml_error')
    if f is not None or gdal.VSIGetLastErrorMsg().find('bla') < 0:
        gdaltest.post_reason('fail')
        print(gdal.VSIGetLastErrorMsg())
        return 'fail'


    handler = webserver.SequentialHandler()
    response = '<?xml version="1.0" encoding="UTF-8"?><oops>'
    response = '%x\r\n%s' % (len(response), response)
    handler.add('GET', '/s3_fake_bucket/invalid_xml_error', 400,
                { 'Content-type': 'application/xml',
                  'Transfer-Encoding': 'chunked' }, response)
    gdal.ErrorReset()
    with webserver.install_http_handler(handler):
        with gdaltest.error_handler():
            f = open_for_read('/vsis3_streaming/s3_fake_bucket/invalid_xml_error')
    if f is not None or gdal.VSIGetLastErrorMsg().find('<oops>') < 0:
        gdaltest.post_reason('fail')
        print(gdal.VSIGetLastErrorMsg())
        return 'fail'


    handler = webserver.SequentialHandler()
    response = '<?xml version="1.0" encoding="UTF-8"?><Error/>'
    response = '%x\r\n%s' % (len(response), response)
    handler.add('GET', '/s3_fake_bucket/no_code_in_error', 400,
                { 'Content-type': 'application/xml',
                  'Transfer-Encoding': 'chunked' }, response)
    gdal.ErrorReset()
    with webserver.install_http_handler(handler):
        with gdaltest.error_handler():
            f = open_for_read('/vsis3_streaming/s3_fake_bucket/no_code_in_error')
    if f is not None or gdal.VSIGetLastErrorMsg().find('<Error/>') < 0:
        gdaltest.post_reason('fail')
        print(gdal.VSIGetLastErrorMsg())
        return 'fail'


    handler = webserver.SequentialHandler()
    response = '<?xml version="1.0" encoding="UTF-8"?><Error><Code>AuthorizationHeaderMalformed</Code></Error>'
    response = '%x\r\n%s' % (len(response), response)
    handler.add('GET', '/s3_fake_bucket/no_region_in_AuthorizationHeaderMalformed_error', 400,
                { 'Content-type': 'application/xml',
                  'Transfer-Encoding': 'chunked' }, response)
    gdal.ErrorReset()
    with webserver.install_http_handler(handler):
        with gdaltest.error_handler():
            f = open_for_read('/vsis3_streaming/s3_fake_bucket/no_region_in_AuthorizationHeaderMalformed_error')
    if f is not None or gdal.VSIGetLastErrorMsg().find('<Error>') < 0:
        gdaltest.post_reason('fail')
        print(gdal.VSIGetLastErrorMsg())
        return 'fail'

    handler = webserver.SequentialHandler()
    response = '<?xml version="1.0" encoding="UTF-8"?><Error><Code>PermanentRedirect</Code></Error>'
    response = '%x\r\n%s' % (len(response), response)
    handler.add('GET', '/s3_fake_bucket/no_endpoint_in_PermanentRedirect_error', 400,
                { 'Content-type': 'application/xml',
                  'Transfer-Encoding': 'chunked' }, response)
    gdal.ErrorReset()
    with webserver.install_http_handler(handler):
        with gdaltest.error_handler():
            f = open_for_read('/vsis3_streaming/s3_fake_bucket/no_endpoint_in_PermanentRedirect_error')
    if f is not None or gdal.VSIGetLastErrorMsg().find('<Error>') < 0:
        gdaltest.post_reason('fail')
        print(gdal.VSIGetLastErrorMsg())
        return 'fail'

    handler = webserver.SequentialHandler()
    response = '<?xml version="1.0" encoding="UTF-8"?><Error><Code>bla</Code></Error>'
    response = '%x\r\n%s' % (len(response), response)
    handler.add('GET', '/s3_fake_bucket/no_message_in_error', 400,
                { 'Content-type': 'application/xml',
                  'Transfer-Encoding': 'chunked' }, response)
    gdal.ErrorReset()
    with webserver.install_http_handler(handler):
        with gdaltest.error_handler():
            f = open_for_read('/vsis3_streaming/s3_fake_bucket/no_message_in_error')
    if f is not None or gdal.VSIGetLastErrorMsg().find('<Error>') < 0:
        gdaltest.post_reason('fail')
        print(gdal.VSIGetLastErrorMsg())
        return 'fail'

    # Test with requester pays
    handler = webserver.SequentialHandler()

    def method(request):
        if 'x-amz-request-payer' not in request.headers:
            sys.stderr.write('Bad headers: %s\n' % str(request.headers))
            request.send_response(403)
            return
        expected_authorization_8080 = 'AWS4-HMAC-SHA256 Credential=AWS_ACCESS_KEY_ID/20150101/us-east-1/s3/aws4_request,SignedHeaders=host;x-amz-content-sha256;x-amz-date;x-amz-request-payer,Signature=cf713a394e1b629ac0e468d60d3d4a12f5236fd72d21b6005c758b0dfc7049cd'
        expected_authorization_8081 = 'AWS4-HMAC-SHA256 Credential=AWS_ACCESS_KEY_ID/20150101/us-east-1/s3/aws4_request,SignedHeaders=host;x-amz-content-sha256;x-amz-date;x-amz-request-payer,Signature=4756166679008a1a40cd6ff91dbbef670a71c11bf8e3c998dd7385577c3ac4d9'
        if request.headers['Authorization'] != expected_authorization_8080 and request.headers['Authorization'] != expected_authorization_8081:
            sys.stderr.write("Bad Authorization: '%s'\n" % str(request.headers['Authorization']))
            request.send_response(403)
            return
        if request.headers['x-amz-request-payer'] != 'requester':
            sys.stderr.write("Bad x-amz-request-payer: '%s'\n" % str(request.headers['x-amz-request-payer']))
            request.send_response(403)
            return

        request.send_response(200)
        request.send_header('Content-type', 'text/plain')
        request.send_header('Content-Length', 3)
        request.end_headers()
        request.wfile.write("""foo""".encode('ascii'))

    handler.add('GET', '/s3_fake_bucket_with_requester_pays/resource', custom_method = method)

    with gdaltest.config_option('AWS_REQUEST_PAYER', 'requester'):
        with webserver.install_http_handler(handler):
            with gdaltest.error_handler():
                f = open_for_read('/vsis3/s3_fake_bucket_with_requester_pays/resource')
                if f is None:
                    gdaltest.post_reason('fail')
                    return 'fail'
                data = gdal.VSIFReadL(1, 3, f).decode('ascii')
                gdal.VSIFCloseL(f)

    if data != 'foo':
        gdaltest.post_reason('fail')
        return 'fail'

    return 'success'

###############################################################################
# Test ReadDir() with a fake AWS server

def vsis3_3():

    if gdaltest.webserver_port == 0:
        return 'skip'

    handler = webserver.SequentialHandler()

    def method(request):
        request.protocol_version = 'HTTP/1.1'
        if request.headers['Authorization'].find('us-east-1') >= 0:
            request.send_response(400)
            response = '<?xml version="1.0" encoding="UTF-8"?><Error><Message>bla</Message><Code>AuthorizationHeaderMalformed</Code><Region>us-west-2</Region></Error>'
            response = '%x\r\n%s' % (len(response), response)
            request.send_header('Content-type', 'application/xml')
            request.send_header('Transfer-Encoding', 'chunked')
            request.end_headers()
            request.wfile.write(response.encode('ascii'))
        elif request.headers['Authorization'].find('us-west-2') >= 0:
            if request.headers['Host'].startswith('127.0.0.1'):
                request.send_response(301)
                response = '<?xml version="1.0" encoding="UTF-8"?><Error><Message>bla</Message><Code>PermanentRedirect</Code><Endpoint>localhost:%d</Endpoint></Error>' % request.server.port
                response = '%x\r\n%s' % (len(response), response)
                request.send_header('Content-type', 'application/xml')
                request.send_header('Transfer-Encoding', 'chunked')
                request.end_headers()
                request.wfile.write(response.encode('ascii'))
            elif request.headers['Host'].startswith('localhost'):
                request.send_response(200)
                request.send_header('Content-type', 'application/xml')
                response = """<?xml version="1.0" encoding="UTF-8"?>
                    <ListBucketResult>
                        <Prefix>a_dir/</Prefix>
                        <NextMarker>bla</NextMarker>
                        <Contents>
                            <Key>a_dir/resource3.bin</Key>
                            <LastModified>1970-01-01T00:00:01.000Z</LastModified>
                            <Size>123456</Size>
                        </Contents>
                    </ListBucketResult>
                """
                request.send_header('Content-Length', len(response))
                request.end_headers()
                request.wfile.write(response.encode('ascii'))
            else:
                sys.stderr.write('Bad headers: %s\n' % str(request.headers))
                request.send_response(403)
        else:
            sys.stderr.write('Bad headers: %s\n' % str(request.headers))
            request.send_response(403)

    handler.add('GET', '/s3_fake_bucket2/?delimiter=/&prefix=a_dir/', custom_method = method)
    handler.add('GET', '/s3_fake_bucket2/?delimiter=/&prefix=a_dir/', custom_method = method)
    handler.add('GET', '/s3_fake_bucket2/?delimiter=/&prefix=a_dir/', custom_method = method)

    def method(request):
        # /vsis3/ should have remembered the change of region and endpoint
        if request.headers['Authorization'].find('us-west-2') < 0 or \
            not request.headers['Host'].startswith('localhost'):
            sys.stderr.write('Bad headers: %s\n' % str(request.headers))
            request.send_response(403)

        request.protocol_version = 'HTTP/1.1'
        request.send_response(200)
        request.send_header('Content-type', 'application/xml')
        response = """<?xml version="1.0" encoding="UTF-8"?>
            <ListBucketResult>
                <Prefix>a_dir/</Prefix>
                <Contents>
                    <Key>a_dir/resource4.bin</Key>
                    <LastModified>2015-10-16T12:34:56.000Z</LastModified>
                    <Size>456789</Size>
                </Contents>
                <CommonPrefixes>
                    <Prefix>a_dir/subdir/</Prefix>
                </CommonPrefixes>
            </ListBucketResult>
        """
        request.send_header('Content-Length', len(response))
        request.end_headers()
        request.wfile.write(response.encode('ascii'))

    handler.add('GET', '/s3_fake_bucket2/?delimiter=/&marker=bla&prefix=a_dir/', custom_method = method)

    with webserver.install_http_handler(handler):
        f = open_for_read('/vsis3/s3_fake_bucket2/a_dir/resource3.bin')
    if f is None:

        if gdaltest.is_travis_branch('trusty'):
            print('Skipped on trusty branch, but should be investigated')
            return 'skip'

        gdaltest.post_reason('fail')
        return 'fail'
    gdal.VSIFCloseL(f)

    with webserver.install_http_handler(webserver.SequentialHandler()):
        dir_contents = gdal.ReadDir('/vsis3/s3_fake_bucket2/a_dir')
    if dir_contents != ['resource3.bin', 'resource4.bin', 'subdir']:
        gdaltest.post_reason('fail')
        print(dir_contents)
        return 'fail'
    if gdal.VSIStatL('/vsis3/s3_fake_bucket2/a_dir/resource3.bin').size != 123456:
        gdaltest.post_reason('fail')
        return 'fail'
    if gdal.VSIStatL('/vsis3/s3_fake_bucket2/a_dir/resource3.bin').mtime != 1:
        gdaltest.post_reason('fail')
        return 'fail'

    # Test CPL_VSIL_CURL_NON_CACHED
    for config_option_value in [ '/vsis3/s3_non_cached/test.txt',
                        '/vsis3/s3_non_cached',
                        '/vsis3/s3_non_cached:/vsis3/unrelated',
                        '/vsis3/unrelated:/vsis3/s3_non_cached',
                        '/vsis3/unrelated:/vsis3/s3_non_cached:/vsis3/unrelated' ]:
      with gdaltest.config_option('CPL_VSIL_CURL_NON_CACHED', config_option_value):

        handler = webserver.SequentialHandler()
        handler.add('GET', '/s3_non_cached/test.txt', 200, {}, 'foo')

        with webserver.install_http_handler(handler):
            f = open_for_read('/vsis3/s3_non_cached/test.txt')
            if f is None:
                gdaltest.post_reason('fail')
                print(config_option_value)
                return 'fail'
            data = gdal.VSIFReadL(1, 3, f).decode('ascii')
            gdal.VSIFCloseL(f)
            if data != 'foo':
                gdaltest.post_reason('fail')
                print(config_option_value)
                print(data)
                return 'fail'

        handler = webserver.SequentialHandler()
        handler.add('GET', '/s3_non_cached/test.txt', 200, {}, 'bar2')

        with webserver.install_http_handler(handler):
            size = gdal.VSIStatL('/vsis3/s3_non_cached/test.txt').size
        if size != 4:
            gdaltest.post_reason('fail')
            print(config_option_value)
            print(size)
            return 'fail'

        handler = webserver.SequentialHandler()
        handler.add('GET', '/s3_non_cached/test.txt', 200, {}, 'foo')

        with webserver.install_http_handler(handler):
            size = gdal.VSIStatL('/vsis3/s3_non_cached/test.txt').size
            if size != 3:
                gdaltest.post_reason('fail')
                print(config_option_value)
                print(data)
                return 'fail'

        handler = webserver.SequentialHandler()
        handler.add('GET', '/s3_non_cached/test.txt', 200, {}, 'bar2')

        with webserver.install_http_handler(handler):
            f = open_for_read('/vsis3/s3_non_cached/test.txt')
            if f is None:
                gdaltest.post_reason('fail')
                print(config_option_value)
                return 'fail'
            data = gdal.VSIFReadL(1, 4, f).decode('ascii')
            gdal.VSIFCloseL(f)
            if data != 'bar2':
                gdaltest.post_reason('fail')
                print(config_option_value)
                print(data)
                return 'fail'

    # Retry without option
    for config_option_value in [ None,
                                '/vsis3/s3_non_cached/bar.txt' ]:
      with gdaltest.config_option('CPL_VSIL_CURL_NON_CACHED', config_option_value):

        handler = webserver.SequentialHandler()
        handler.add('GET', '/s3_non_cached/?delimiter=/', 200, { 'Content-type': 'application/xml' },
                    """<?xml version="1.0" encoding="UTF-8"?>
                    <ListBucketResult>
                        <Prefix>/</Prefix>
                        <Contents>
                            <Key>/test.txt</Key>
                            <LastModified>1970-01-01T00:00:01.000Z</LastModified>
                            <Size>40</Size>
                        </Contents>
                        <Contents>
                            <Key>/test2.txt</Key>
                            <LastModified>1970-01-01T00:00:01.000Z</LastModified>
                            <Size>40</Size>
                        </Contents>
                    </ListBucketResult>
                """)
        handler.add('GET', '/s3_non_cached/test.txt', 200, {}, 'foo')

        with webserver.install_http_handler(handler):
            f = open_for_read('/vsis3/s3_non_cached/test.txt')
            if f is None:
                gdaltest.post_reason('fail')
                print(config_option_value)
                return 'fail'
            data = gdal.VSIFReadL(1, 3, f).decode('ascii')
            gdal.VSIFCloseL(f)
            if data != 'foo':
                gdaltest.post_reason('fail')
                print(config_option_value)
                print(data)
                return 'fail'

        handler = webserver.SequentialHandler()
        handler.add('GET', '/s3_non_cached/?delimiter=/', 200, { 'Content-type': 'application/xml' },
                    """<?xml version="1.0" encoding="UTF-8"?>
                    <ListBucketResult>
                        <Prefix>/</Prefix>
                        <Contents>
                            <Key>/test.txt</Key>
                            <LastModified>1970-01-01T00:00:01.000Z</LastModified>
                            <Size>30</Size>
                        </Contents>
                    </ListBucketResult>
                """)
        handler.add('GET', '/s3_non_cached/test.txt', 200, {}, 'bar2')

        with webserver.install_http_handler(handler):
            f = open_for_read('/vsis3/s3_non_cached/test.txt')
            if f is None:
                gdaltest.post_reason('fail')
                print(config_option_value)
                return 'fail'
            data = gdal.VSIFReadL(1, 4, f).decode('ascii')
            gdal.VSIFCloseL(f)
            # We should still get foo because of caching
            if data != 'foo':
                gdaltest.post_reason('fail')
                print(config_option_value)
                print(data)
                return 'fail'

    return 'success'

###############################################################################
# Test simple PUT support with a fake AWS server

def vsis3_4():

    if gdaltest.webserver_port == 0:
        return 'skip'

    with webserver.install_http_handler(webserver.SequentialHandler()):
        with gdaltest.error_handler():
            f = gdal.VSIFOpenL('/vsis3/s3_fake_bucket3', 'wb')
    if f is not None:
        gdaltest.post_reason('fail')
        return 'fail'

    handler = webserver.SequentialHandler()
    handler.add('GET', '/s3_fake_bucket3/empty_file.bin', 200, {}, 'foo')
    with webserver.install_http_handler(handler):
        if gdal.VSIStatL('/vsis3/s3_fake_bucket3/empty_file.bin').size != 3:
            gdaltest.post_reason('fail')
            return 'fail'

    # Empty file
    handler = webserver.SequentialHandler()

    def method(request):
        if request.headers['Content-Length'] != '0':
            sys.stderr.write('Did not get expected headers: %s\n' % str(request.headers))
            request.send_response(400)
            return

        request.send_response(200)
        request.end_headers()

    handler.add('PUT', '/s3_fake_bucket3/empty_file.bin', custom_method = method)

    with webserver.install_http_handler(handler):
        f = gdal.VSIFOpenL('/vsis3/s3_fake_bucket3/empty_file.bin', 'wb')
        if f is None:
            gdaltest.post_reason('fail')
            return 'fail'
        gdal.ErrorReset()
        gdal.VSIFCloseL(f)
    if gdal.GetLastErrorMsg() != '':
        gdaltest.post_reason('fail')
        return 'fail'

    handler = webserver.SequentialHandler()
    handler.add('GET', '/s3_fake_bucket3/empty_file.bin', 200, {}, '')
    with webserver.install_http_handler(handler):
        if gdal.VSIStatL('/vsis3/s3_fake_bucket3/empty_file.bin').size != 0:
            gdaltest.post_reason('fail')
            return 'fail'

    # Invalid seek
    handler = webserver.SequentialHandler()
    with webserver.install_http_handler(handler):
        f = gdal.VSIFOpenL('/vsis3/s3_fake_bucket3/empty_file.bin', 'wb')
        if f is None:
            gdaltest.post_reason('fail')
            return 'fail'
        with gdaltest.error_handler():
            ret = gdal.VSIFSeekL(f, 1, 0)
        if ret == 0:
            gdaltest.post_reason('fail')
            return 'fail'
        gdal.VSIFCloseL(f)

    # Invalid read
    handler = webserver.SequentialHandler()
    with webserver.install_http_handler(handler):
        f = gdal.VSIFOpenL('/vsis3/s3_fake_bucket3/empty_file.bin', 'wb')
        if f is None:
            gdaltest.post_reason('fail')
            return 'fail'
        with gdaltest.error_handler():
            ret = gdal.VSIFReadL(1, 1, f)
        if len(ret) != 0:
            gdaltest.post_reason('fail')
            return 'fail'
        gdal.VSIFCloseL(f)

    # Error case
    handler = webserver.SequentialHandler()
    handler.add('PUT', '/s3_fake_bucket3/empty_file_error.bin', 403)
    with webserver.install_http_handler(handler):
        f = gdal.VSIFOpenL('/vsis3/s3_fake_bucket3/empty_file_error.bin', 'wb')
        if f is None:
            gdaltest.post_reason('fail')
            return 'fail'
        gdal.ErrorReset()
        with gdaltest.error_handler():
            gdal.VSIFCloseL(f)
    if gdal.GetLastErrorMsg() == '':
        gdaltest.post_reason('fail')
        return 'fail'

    # Nominal case
    with webserver.install_http_handler(webserver.SequentialHandler()):
        f = gdal.VSIFOpenL('/vsis3/s3_fake_bucket3/another_file.bin', 'wb')
        if f is None:
            gdaltest.post_reason('fail')
            return 'fail'
        if gdal.VSIFSeekL(f, gdal.VSIFTellL(f), 0) != 0:
            gdaltest.post_reason('fail')
            return 'fail'
        if gdal.VSIFSeekL(f, 0, 1) != 0:
            gdaltest.post_reason('fail')
            return 'fail'
        if gdal.VSIFSeekL(f, 0, 2) != 0:
            gdaltest.post_reason('fail')
            return 'fail'
        if gdal.VSIFWriteL('foo', 1, 3, f) != 3:
            gdaltest.post_reason('fail')
            return 'fail'
        if gdal.VSIFWriteL('bar', 1, 3, f) != 3:
            gdaltest.post_reason('fail')
            return 'fail'

    handler = webserver.SequentialHandler()

    def method(request):
        if request.headers['Content-Length'] != '6':
            sys.stderr.write('Did not get expected headers: %s\n' % str(request.headers))
            request.send_response(400)
            return

        content = request.rfile.read(6).decode('ascii')
        if content != 'foobar':
            sys.stderr.write('Did not get expected content: %s\n' % content)
            request.send_response(400)
            return

        request.send_response(200)
        request.end_headers()

    handler.add('PUT', '/s3_fake_bucket3/another_file.bin', custom_method = method)

    gdal.ErrorReset()
    with webserver.install_http_handler(handler):
        gdal.VSIFCloseL(f)
    if gdal.GetLastErrorMsg() != '':
        gdaltest.post_reason('fail')
        return 'fail'

    # Redirect case
    with webserver.install_http_handler(webserver.SequentialHandler()):
        f = gdal.VSIFOpenL('/vsis3/s3_fake_bucket3/redirect', 'wb')
        if f is None:
            gdaltest.post_reason('fail')
            return 'fail'
        if gdal.VSIFWriteL('foobar', 1, 6, f) != 6:
            gdaltest.post_reason('fail')
            return 'fail'

    handler = webserver.SequentialHandler()

    def method(request):
        request.protocol_version = 'HTTP/1.1'
        if request.headers['Authorization'].find('us-east-1') >= 0:
            request.send_response(400)
            response = '<?xml version="1.0" encoding="UTF-8"?><Error><Message>bla</Message><Code>AuthorizationHeaderMalformed</Code><Region>us-west-2</Region></Error>'
            response = '%x\r\n%s' % (len(response), response)
            request.send_header('Content-type', 'application/xml')
            request.send_header('Transfer-Encoding', 'chunked')
            request.end_headers()
            request.wfile.write(response.encode('ascii'))
        elif request.headers['Authorization'].find('us-west-2') >= 0:
            if request.headers['Content-Length'] != '6':
                sys.stderr.write('Did not get expected headers: %s\n' % str(request.headers))
                request.send_response(400)
                return
            request.send_response(200)
            request.end_headers()
        else:
            sys.stderr.write('Bad headers: %s\n' % str(request.headers))
            request.send_response(403)

    handler.add('PUT', '/s3_fake_bucket3/redirect', custom_method = method)
    handler.add('PUT', '/s3_fake_bucket3/redirect', custom_method = method)

    gdal.ErrorReset()
    with webserver.install_http_handler(handler):
        gdal.VSIFCloseL(f)
    if gdal.GetLastErrorMsg() != '':
        gdaltest.post_reason('fail')
        return 'fail'

    return 'success'

###############################################################################
# Test simple DELETE support with a fake AWS server

def vsis3_5():

    if gdaltest.webserver_port == 0:
        return 'skip'

    with webserver.install_http_handler(webserver.SequentialHandler()):
        with gdaltest.error_handler():
            ret = gdal.Unlink('/vsis3/foo')
    if ret == 0:
        gdaltest.post_reason('fail')
        return 'fail'

    handler = webserver.SequentialHandler()
    handler.add('GET', '/s3_delete_bucket/delete_file', 200, {}, 'foo')
    with webserver.install_http_handler(handler):
        if gdal.VSIStatL('/vsis3/s3_delete_bucket/delete_file').size != 3:
            gdaltest.post_reason('fail')
            return 'fail'

    with webserver.install_http_handler(webserver.SequentialHandler()):
        if gdal.VSIStatL('/vsis3/s3_delete_bucket/delete_file').size != 3:
            gdaltest.post_reason('fail')
            return 'fail'

    handler = webserver.SequentialHandler()
    handler.add('DELETE', '/s3_delete_bucket/delete_file', 204)
    with webserver.install_http_handler(handler):
        ret = gdal.Unlink('/vsis3/s3_delete_bucket/delete_file')
    if ret != 0:
        gdaltest.post_reason('fail')
        return 'fail'


    handler = webserver.SequentialHandler()
    handler.add('GET', '/s3_delete_bucket/delete_file', 404, {}, 'foo')
    with webserver.install_http_handler(handler):
        if gdal.VSIStatL('/vsis3/s3_delete_bucket/delete_file') is not None:
            gdaltest.post_reason('fail')
            return 'fail'

    handler = webserver.SequentialHandler()
    handler.add('DELETE', '/s3_delete_bucket/delete_file_error', 403)
    with webserver.install_http_handler(handler):
        with gdaltest.error_handler():
            ret = gdal.Unlink('/vsis3/s3_delete_bucket/delete_file_error')
    if ret == 0:
        gdaltest.post_reason('fail')
        return 'fail'


    handler = webserver.SequentialHandler()

    def method(request):
        request.protocol_version = 'HTTP/1.1'
        if request.headers['Authorization'].find('us-east-1') >= 0:
            request.send_response(400)
            response = '<?xml version="1.0" encoding="UTF-8"?><Error><Message>bla</Message><Code>AuthorizationHeaderMalformed</Code><Region>us-west-2</Region></Error>'
            response = '%x\r\n%s' % (len(response), response)
            request.send_header('Content-type', 'application/xml')
            request.send_header('Transfer-Encoding', 'chunked')
            request.end_headers()
            request.wfile.write(response.encode('ascii'))
        elif request.headers['Authorization'].find('us-west-2') >= 0:
            request.send_response(204)
            request.end_headers()
        else:
            sys.stderr.write('Bad headers: %s\n' % str(request.headers))
            request.send_response(403)

    handler.add('DELETE', '/s3_delete_bucket/redirect', custom_method = method)
    handler.add('DELETE', '/s3_delete_bucket/redirect', custom_method = method)

    with webserver.install_http_handler(handler):
        ret = gdal.Unlink('/vsis3/s3_delete_bucket/redirect')
    if ret != 0:
        gdaltest.post_reason('fail')
        return 'fail'

    return 'success'

###############################################################################
# Test multipart upload with a fake AWS server

def vsis3_6():

    if gdaltest.webserver_port == 0:
        return 'skip'

    with gdaltest.config_option('VSIS3_CHUNK_SIZE', '1'): # 1 MB
        with webserver.install_http_handler(webserver.SequentialHandler()):
            f = gdal.VSIFOpenL('/vsis3/s3_fake_bucket4/large_file.bin', 'wb')
    if f is None:
        gdaltest.post_reason('fail')
        return 'fail'
    size = 1024*1024+1

    handler = webserver.SequentialHandler()

    def method(request):
        request.protocol_version = 'HTTP/1.1'
        if request.headers['Authorization'].find('us-east-1') >= 0:
            request.send_response(400)
            response = '<?xml version="1.0" encoding="UTF-8"?><Error><Message>bla</Message><Code>AuthorizationHeaderMalformed</Code><Region>us-west-2</Region></Error>'
            response = '%x\r\n%s' % (len(response), response)
            request.send_header('Content-type', 'application/xml')
            request.send_header('Transfer-Encoding', 'chunked')
            request.end_headers()
            request.wfile.write(response.encode('ascii'))
        elif request.headers['Authorization'].find('us-west-2') >= 0:
            response = '<?xml version="1.0" encoding="UTF-8"?><InitiateMultipartUploadResult><UploadId>my_id</UploadId></InitiateMultipartUploadResult>'
            request.send_response(200)
            request.send_header('Content-type', 'application/xml')
            request.send_header('Content-Length', len(response))
            request.end_headers()
            request.wfile.write(response.encode('ascii'))
        else:
            sys.stderr.write('Bad headers: %s\n' % str(request.headers))
            request.send_response(403)

    handler.add('POST', '/s3_fake_bucket4/large_file.bin?uploads', custom_method = method)
    handler.add('POST', '/s3_fake_bucket4/large_file.bin?uploads', custom_method = method)

    def method(request):
        if request.headers['Content-Length'] != '1048576':
            sys.stderr.write('Did not get expected headers: %s\n' % str(request.headers))
            request.send_response(400)
            return
        request.send_response(200)
        request.send_header('ETag', '"first_etag"')
        request.end_headers()

    handler.add('PUT', '/s3_fake_bucket4/large_file.bin?partNumber=1&uploadId=my_id', custom_method = method)

    with webserver.install_http_handler(handler):
        ret = gdal.VSIFWriteL(''.join('a' for i in range(size)), 1,size, f)
    if ret != size:
        gdaltest.post_reason('fail')
        return 'fail'
    handler = webserver.SequentialHandler()

    def method(request):
        if request.headers['Content-Length'] != '1':
            sys.stderr.write('Did not get expected headers: %s\n' % str(request.headers))
            request.send_response(400)
            return
        request.send_response(200)
        request.send_header('ETag', '"second_etag"')
        request.end_headers()

    handler.add('PUT', '/s3_fake_bucket4/large_file.bin?partNumber=2&uploadId=my_id', custom_method = method)

    def method(request):

        if request.headers['Content-Length'] != '186':
            sys.stderr.write('Did not get expected headers: %s\n' % str(request.headers))
            request.send_response(400)
            return

        content = request.rfile.read(186).decode('ascii')
        if content != """<CompleteMultipartUpload>
<Part>
<PartNumber>1</PartNumber><ETag>"first_etag"</ETag></Part>
<Part>
<PartNumber>2</PartNumber><ETag>"second_etag"</ETag></Part>
</CompleteMultipartUpload>
""":
            sys.stderr.write('Did not get expected content: %s\n' % content)
            request.send_response(400)
            return

        request.send_response(200)
        request.end_headers()

    handler.add('POST', '/s3_fake_bucket4/large_file.bin?uploadId=my_id', custom_method = method)

    gdal.ErrorReset()
    with webserver.install_http_handler(handler):
        gdal.VSIFCloseL(f)
    if gdal.GetLastErrorMsg() != '':
        gdaltest.post_reason('fail')
        return 'fail'

    handler = webserver.SequentialHandler()
    handler.add('POST', '/s3_fake_bucket4/large_file_initiate_403_error.bin?uploads', 403)
    handler.add('POST', '/s3_fake_bucket4/large_file_initiate_empty_result.bin?uploads', 200)
    handler.add('POST', '/s3_fake_bucket4/large_file_initiate_invalid_xml_result.bin?uploads', 200, {}, 'foo')
    handler.add('POST', '/s3_fake_bucket4/large_file_initiate_no_uploadId.bin?uploads', 200, {}, '<foo/>')
    with webserver.install_http_handler(handler):
      for filename in [ '/vsis3/s3_fake_bucket4/large_file_initiate_403_error.bin',
                        '/vsis3/s3_fake_bucket4/large_file_initiate_empty_result.bin',
                        '/vsis3/s3_fake_bucket4/large_file_initiate_invalid_xml_result.bin',
                        '/vsis3/s3_fake_bucket4/large_file_initiate_no_uploadId.bin' ]:
        with gdaltest.config_option('VSIS3_CHUNK_SIZE', '1'): # 1 MB
            f = gdal.VSIFOpenL(filename, 'wb')
        if f is None:
            gdaltest.post_reason('fail')
            return 'fail'
        size = 1024*1024+1
        with gdaltest.error_handler():
            ret = gdal.VSIFWriteL(''.join('a' for i in range(size)), 1,size, f)
        if ret != 0:
            gdaltest.post_reason('fail')
            print(ret)
            return 'fail'
        gdal.ErrorReset()
        gdal.VSIFCloseL(f)
        if gdal.GetLastErrorMsg() != '':
            gdaltest.post_reason('fail')
            return 'fail'

    handler = webserver.SequentialHandler()
    handler.add('POST', '/s3_fake_bucket4/large_file_upload_part_403_error.bin?uploads', 200, {},
                '<?xml version="1.0" encoding="UTF-8"?><InitiateMultipartUploadResult><UploadId>my_id</UploadId></InitiateMultipartUploadResult>')
    handler.add('PUT', '/s3_fake_bucket4/large_file_upload_part_403_error.bin?partNumber=1&uploadId=my_id', 403)
    handler.add('DELETE', '/s3_fake_bucket4/large_file_upload_part_403_error.bin?uploadId=my_id', 204)

    handler.add('POST', '/s3_fake_bucket4/large_file_upload_part_no_etag.bin?uploads', 200, {},
                '<?xml version="1.0" encoding="UTF-8"?><InitiateMultipartUploadResult><UploadId>my_id</UploadId></InitiateMultipartUploadResult>')
    handler.add('PUT', '/s3_fake_bucket4/large_file_upload_part_no_etag.bin?partNumber=1&uploadId=my_id', 200)
    handler.add('DELETE', '/s3_fake_bucket4/large_file_upload_part_no_etag.bin?uploadId=my_id', 204)

    with webserver.install_http_handler(handler):
      for filename in [ '/vsis3/s3_fake_bucket4/large_file_upload_part_403_error.bin',
                      '/vsis3/s3_fake_bucket4/large_file_upload_part_no_etag.bin']:
        with gdaltest.config_option('VSIS3_CHUNK_SIZE', '1'): # 1 MB
            f = gdal.VSIFOpenL(filename, 'wb')
        if f is None:
            gdaltest.post_reason('fail')
            return 'fail'
        size = 1024*1024+1
        with gdaltest.error_handler():
            ret = gdal.VSIFWriteL(''.join('a' for i in range(size)), 1,size, f)
        if ret != 0:
            gdaltest.post_reason('fail')
            print(ret)
            return 'fail'
        gdal.ErrorReset()
        gdal.VSIFCloseL(f)
        if gdal.GetLastErrorMsg() != '':
            gdaltest.post_reason('fail')
            return 'fail'

    return 'success'

###############################################################################
# Read credentials from simulated ~/.aws/credentials

def vsis3_read_credentials_file():

    if gdaltest.webserver_port == 0:
        return 'skip'

    gdal.SetConfigOption('AWS_SECRET_ACCESS_KEY', '')
    gdal.SetConfigOption('AWS_ACCESS_KEY_ID', '')

    gdal.SetConfigOption('CPL_AWS_CREDENTIALS_FILE', '/vsimem/aws_credentials')

    gdal.VSICurlClearCache()

    gdal.FileFromMemBuffer('/vsimem/aws_credentials', """
[unrelated]
aws_access_key_id = foo
aws_secret_access_key = bar
[default]
aws_access_key_id = AWS_ACCESS_KEY_ID
aws_secret_access_key = AWS_SECRET_ACCESS_KEY
[unrelated]
aws_access_key_id = foo
aws_secret_access_key = bar
""")

    handler = webserver.SequentialHandler()
    handler.add('GET', '/s3_fake_bucket/resource', custom_method = get_s3_fake_bucket_resource_method)
    with webserver.install_http_handler(handler):
        f = open_for_read('/vsis3/s3_fake_bucket/resource')
        if f is None:
            gdaltest.post_reason('fail')
            return 'fail'
        data = gdal.VSIFReadL(1, 4, f).decode('ascii')
        gdal.VSIFCloseL(f)

    if data != 'foo':
        gdaltest.post_reason('fail')
        print(data)
        return 'fail'

    gdal.SetConfigOption('CPL_AWS_CREDENTIALS_FILE', '')
    gdal.Unlink('/vsimem/aws_credentials')

    return 'success'

###############################################################################
# Read credentials from simulated  ~/.aws/config

def vsis3_read_config_file():

    if gdaltest.webserver_port == 0:
        return 'skip'

    gdal.SetConfigOption('AWS_SECRET_ACCESS_KEY', '')
    gdal.SetConfigOption('AWS_ACCESS_KEY_ID', '')

    gdal.SetConfigOption('AWS_CONFIG_FILE', '/vsimem/aws_config')

    gdal.VSICurlClearCache()

    gdal.FileFromMemBuffer('/vsimem/aws_config', """
[unrelated]
aws_access_key_id = foo
aws_secret_access_key = bar
[default]
aws_access_key_id = AWS_ACCESS_KEY_ID
aws_secret_access_key = AWS_SECRET_ACCESS_KEY
region = us-east-1
[unrelated]
aws_access_key_id = foo
aws_secret_access_key = bar
""")

    handler = webserver.SequentialHandler()
    handler.add('GET', '/s3_fake_bucket/resource', custom_method = get_s3_fake_bucket_resource_method)
    with webserver.install_http_handler(handler):
        f = open_for_read('/vsis3/s3_fake_bucket/resource')
        if f is None:
            gdaltest.post_reason('fail')
            return 'fail'
        data = gdal.VSIFReadL(1, 4, f).decode('ascii')
        gdal.VSIFCloseL(f)

    if data != 'foo':
        gdaltest.post_reason('fail')
        print(data)
        return 'fail'

    gdal.SetConfigOption('AWS_CONFIG_FILE', '')
    gdal.Unlink('/vsimem/aws_config')

    return 'success'

###############################################################################
# Read credentials from simulated ~/.aws/credentials and ~/.aws/config

def vsis3_read_credentials_config_file():

    if gdaltest.webserver_port == 0:
        return 'skip'

    gdal.SetConfigOption('AWS_SECRET_ACCESS_KEY', '')
    gdal.SetConfigOption('AWS_ACCESS_KEY_ID', '')

    gdal.SetConfigOption('CPL_AWS_CREDENTIALS_FILE', '/vsimem/aws_credentials')
    gdal.SetConfigOption('AWS_CONFIG_FILE', '/vsimem/aws_config')

    gdal.VSICurlClearCache()

    gdal.FileFromMemBuffer('/vsimem/aws_credentials', """
[unrelated]
aws_access_key_id = foo
aws_secret_access_key = bar
[default]
aws_access_key_id = AWS_ACCESS_KEY_ID
aws_secret_access_key = AWS_SECRET_ACCESS_KEY
[unrelated]
aws_access_key_id = foo
aws_secret_access_key = bar
""")

    gdal.FileFromMemBuffer('/vsimem/aws_config', """
[unrelated]
aws_access_key_id = foo
aws_secret_access_key = bar
[default]
aws_access_key_id = AWS_ACCESS_KEY_ID
aws_secret_access_key = AWS_SECRET_ACCESS_KEY
region = us-east-1
[unrelated]
aws_access_key_id = foo
aws_secret_access_key = bar
""")

    handler = webserver.SequentialHandler()
    handler.add('GET', '/s3_fake_bucket/resource', custom_method = get_s3_fake_bucket_resource_method)
    with webserver.install_http_handler(handler):
        f = open_for_read('/vsis3/s3_fake_bucket/resource')
        if f is None:
            gdaltest.post_reason('fail')
            return 'fail'
        data = gdal.VSIFReadL(1, 4, f).decode('ascii')
        gdal.VSIFCloseL(f)

    if data != 'foo':
        gdaltest.post_reason('fail')
        print(data)
        return 'fail'

    gdal.SetConfigOption('CPL_AWS_CREDENTIALS_FILE', '')
    gdal.Unlink('/vsimem/aws_credentials')
    gdal.SetConfigOption('AWS_CONFIG_FILE', '')
    gdal.Unlink('/vsimem/aws_config')

    return 'success'

###############################################################################
# Read credentials from simulated ~/.aws/credentials and ~/.aws/config with
# a non default profile

def vsis3_read_credentials_config_file_non_default():

    if gdaltest.webserver_port == 0:
        return 'skip'

    gdal.SetConfigOption('AWS_SECRET_ACCESS_KEY', '')
    gdal.SetConfigOption('AWS_ACCESS_KEY_ID', '')

    gdal.SetConfigOption('CPL_AWS_CREDENTIALS_FILE', '/vsimem/aws_credentials')
    gdal.SetConfigOption('AWS_CONFIG_FILE', '/vsimem/aws_config')
    gdal.SetConfigOption('AWS_DEFAULT_PROFILE', 'myprofile')

    gdal.VSICurlClearCache()

    gdal.FileFromMemBuffer('/vsimem/aws_credentials', """
[unrelated]
aws_access_key_id = foo
aws_secret_access_key = bar
[myprofile]
aws_access_key_id = AWS_ACCESS_KEY_ID
aws_secret_access_key = AWS_SECRET_ACCESS_KEY
[default]
aws_access_key_id = foo
aws_secret_access_key = bar
""")

    gdal.FileFromMemBuffer('/vsimem/aws_config', """
[unrelated]
aws_access_key_id = foo
aws_secret_access_key = bar
[profile myprofile]
region = us-east-1
[default]
aws_access_key_id = foo
aws_secret_access_key = bar
""")

    handler = webserver.SequentialHandler()
    handler.add('GET', '/s3_fake_bucket/resource', custom_method = get_s3_fake_bucket_resource_method)
    with webserver.install_http_handler(handler):
        f = open_for_read('/vsis3/s3_fake_bucket/resource')
        if f is None:
            gdaltest.post_reason('fail')
            return 'fail'
        data = gdal.VSIFReadL(1, 4, f).decode('ascii')
        gdal.VSIFCloseL(f)

    if data != 'foo':
        gdaltest.post_reason('fail')
        print(data)
        return 'fail'

    gdal.SetConfigOption('CPL_AWS_CREDENTIALS_FILE', '')
    gdal.Unlink('/vsimem/aws_credentials')
    gdal.SetConfigOption('AWS_CONFIG_FILE', '')
    gdal.Unlink('/vsimem/aws_config')
    gdal.SetConfigOption('AWS_DEFAULT_PROFILE', '')

    return 'success'

###############################################################################
# Read credentials from simulated ~/.aws/credentials and ~/.aws/config

def vsis3_read_credentials_config_file_inconsistent():

    if gdaltest.webserver_port == 0:
        return 'skip'

    gdal.SetConfigOption('AWS_SECRET_ACCESS_KEY', '')
    gdal.SetConfigOption('AWS_ACCESS_KEY_ID', '')

    gdal.SetConfigOption('CPL_AWS_CREDENTIALS_FILE', '/vsimem/aws_credentials')
    gdal.SetConfigOption('AWS_CONFIG_FILE', '/vsimem/aws_config')

    gdal.VSICurlClearCache()

    gdal.FileFromMemBuffer('/vsimem/aws_credentials', """
[unrelated]
aws_access_key_id = foo
aws_secret_access_key = bar
[default]
aws_access_key_id = AWS_ACCESS_KEY_ID
aws_secret_access_key = AWS_SECRET_ACCESS_KEY
[unrelated]
aws_access_key_id = foo
aws_secret_access_key = bar
""")

    gdal.FileFromMemBuffer('/vsimem/aws_config', """
[unrelated]
aws_access_key_id = foo
aws_secret_access_key = bar
[default]
aws_access_key_id = AWS_ACCESS_KEY_ID_inconsistent
aws_secret_access_key = AWS_SECRET_ACCESS_KEY_inconsistent
region = us-east-1
[unrelated]
aws_access_key_id = foo
aws_secret_access_key = bar
""")

    gdal.ErrorReset()
    handler = webserver.SequentialHandler()
    handler.add('GET', '/s3_fake_bucket/resource', custom_method = get_s3_fake_bucket_resource_method)
    with webserver.install_http_handler(handler):
        with gdaltest.error_handler():
            f = open_for_read('/vsis3/s3_fake_bucket/resource')
        if f is None:
            gdaltest.post_reason('fail')
            return 'fail'
        if gdal.GetLastErrorMsg() == '':
            # Expected 'aws_access_key_id defined in both /vsimem/aws_credentials and /vsimem/aws_config'
            gdaltest.post_reason('fail')
            return 'fail'
        data = gdal.VSIFReadL(1, 4, f).decode('ascii')
        gdal.VSIFCloseL(f)

    if data != 'foo':
        gdaltest.post_reason('fail')
        print(data)
        return 'fail'

    gdal.SetConfigOption('CPL_AWS_CREDENTIALS_FILE', '')
    gdal.Unlink('/vsimem/aws_credentials')
    gdal.SetConfigOption('AWS_CONFIG_FILE', '')
    gdal.Unlink('/vsimem/aws_config')

    return 'success'

###############################################################################
# Read credentials from simulated EC2 instance

def vsis3_read_credentials_ec2():

    if gdaltest.webserver_port == 0:
        return 'skip'

    if sys.platform not in ('linux', 'linux2', 'win32'):
        return 'skip'

    gdal.SetConfigOption('CPL_AWS_CREDENTIALS_FILE', '')
    gdal.SetConfigOption('AWS_CONFIG_FILE', '')
    gdal.SetConfigOption('AWS_SECRET_ACCESS_KEY', '')
    gdal.SetConfigOption('AWS_ACCESS_KEY_ID', '')

    gdal.SetConfigOption('CPL_AWS_EC2_CREDENTIALS_URL',
                         'http://localhost:%d/latest/meta-data/iam/security-credentials/' % gdaltest.webserver_port)
    # Disable hypervisor related check to test if we are really on EC2
    gdal.SetConfigOption('CPL_AWS_CHECK_HYPERVISOR_UUID', 'NO')

    gdal.VSICurlClearCache()

    handler = webserver.SequentialHandler()
    handler.add('GET', '/latest/meta-data/iam/security-credentials/', 200, {}, 'myprofile')
    handler.add('GET', '/latest/meta-data/iam/security-credentials/myprofile', 200, {},
                """{
                "AccessKeyId": "AWS_ACCESS_KEY_ID",
                "SecretAccessKey": "AWS_SECRET_ACCESS_KEY",
                "Expiration": "3000-01-01T00:00:00Z"
                }""")
    handler.add('GET', '/s3_fake_bucket/resource', custom_method = get_s3_fake_bucket_resource_method)
    with webserver.install_http_handler(handler):
        f = open_for_read('/vsis3/s3_fake_bucket/resource')
        if f is None:
            gdaltest.post_reason('fail')
            return 'fail'
        data = gdal.VSIFReadL(1, 4, f).decode('ascii')
        gdal.VSIFCloseL(f)

    if data != 'foo':
        gdaltest.post_reason('fail')
        print(data)
        return 'fail'

    # Set a fake URL to check that credentials re-use works
    gdal.SetConfigOption('CPL_AWS_EC2_CREDENTIALS_URL', '')


    handler = webserver.SequentialHandler()
    handler.add('GET', '/s3_fake_bucket/bar', 200, {}, 'bar')
    with webserver.install_http_handler(handler):
        f = open_for_read('/vsis3/s3_fake_bucket/bar')
        if f is None:
            gdaltest.post_reason('fail')
            return 'fail'
        data = gdal.VSIFReadL(1, 4, f).decode('ascii')
        gdal.VSIFCloseL(f)

    if data != 'bar':
        gdaltest.post_reason('fail')
        print(data)
        return 'fail'

    gdal.SetConfigOption('CPL_AWS_EC2_CREDENTIALS_URL','')
    gdal.SetConfigOption('CPL_AWS_CHECK_HYPERVISOR_UUID', None)

    return 'success'

###############################################################################
# Read credentials from simulated EC2 instance with expiration of the
# cached credentials

def vsis3_read_credentials_ec2_expiration():

    if gdaltest.webserver_port == 0:
        return 'skip'

    if sys.platform not in ('linux', 'linux2', 'win32'):
        return 'skip'

    gdal.SetConfigOption('CPL_AWS_CREDENTIALS_FILE', '')
    gdal.SetConfigOption('AWS_CONFIG_FILE', '')
    gdal.SetConfigOption('AWS_SECRET_ACCESS_KEY', '')
    gdal.SetConfigOption('AWS_ACCESS_KEY_ID', '')

    gdal.SetConfigOption('CPL_AWS_EC2_CREDENTIALS_URL',
                         'http://localhost:%d/latest/meta-data/iam/security-credentials/expire_in_past/' % gdaltest.webserver_port)
    # Disable hypervisor related check to test if we are really on EC2
    gdal.SetConfigOption('CPL_AWS_CHECK_HYPERVISOR_UUID', 'NO')

    gdal.VSICurlClearCache()

    handler = webserver.SequentialHandler()
    handler.add('GET', '/latest/meta-data/iam/security-credentials/expire_in_past/', 200, {}, 'myprofile')
    handler.add('GET', '/latest/meta-data/iam/security-credentials/expire_in_past/myprofile', 200, {},
                """{
                "AccessKeyId": "AWS_ACCESS_KEY_ID",
                "SecretAccessKey": "AWS_SECRET_ACCESS_KEY",
                "Expiration": "1970-01-01T00:00:00Z"
                }""")
    handler.add('GET', '/s3_fake_bucket/resource', custom_method = get_s3_fake_bucket_resource_method)
    with webserver.install_http_handler(handler):
        f = open_for_read('/vsis3/s3_fake_bucket/resource')
        if f is None:
            gdaltest.post_reason('fail')
            return 'fail'
        data = gdal.VSIFReadL(1, 4, f).decode('ascii')
        gdal.VSIFCloseL(f)

    if data != 'foo':
        gdaltest.post_reason('fail')
        print(data)
        return 'fail'

    # Set a fake URL to demonstrate we try to re-fetch credentials
    gdal.SetConfigOption('CPL_AWS_EC2_CREDENTIALS_URL', '')

    with gdaltest.error_handler():
        f = open_for_read('/vsis3/s3_fake_bucket/bar')
    if f is not None:
        gdaltest.post_reason('fail')
        return 'fail'

    gdal.SetConfigOption('CPL_AWS_EC2_CREDENTIALS_URL','')
    gdal.SetConfigOption('CPL_AWS_CHECK_HYPERVISOR_UUID', None)

    return 'success'

###############################################################################
def vsis3_stop_webserver():

    if gdaltest.webserver_port == 0:
        return 'skip'

    webserver.server_stop(gdaltest.webserver_process, gdaltest.webserver_port)

    return 'success'

###############################################################################
# Nominal cases (require valid credentials)

def vsis3_extra_1():
    try:
        drv = gdal.GetDriverByName( 'HTTP' )
    except:
        drv = None

    if drv is None:
        return 'skip'

    credentials_filename = gdal.GetConfigOption('HOME',
        gdal.GetConfigOption('USERPROFILE', '')) + '/.aws/credentials'

    # Either a bucket name or bucket/filename
    s3_resource = gdal.GetConfigOption('S3_RESOURCE')

    if not os.path.exists(credentials_filename):
        if gdal.GetConfigOption('AWS_SECRET_ACCESS_KEY') is None:
            print('Missing AWS_SECRET_ACCESS_KEY for running gdaltest_list_extra')
            return 'skip'
        elif gdal.GetConfigOption('AWS_ACCESS_KEY_ID') is None:
            print('Missing AWS_ACCESS_KEY_ID for running gdaltest_list_extra')
            return 'skip'
    elif s3_resource is None:
        print('Missing S3_RESOURCE for running gdaltest_list_extra')
        return 'skip'

    f = open_for_read('/vsis3/' + s3_resource)
    if f is None:
        gdaltest.post_reason('fail')
        print('cannot open %s' % ('/vsis3/' + s3_resource))
        return 'fail'
    ret = gdal.VSIFReadL(1, 1, f)
    gdal.VSIFCloseL(f)

    if len(ret) != 1:
        gdaltest.post_reason('fail')
        print(ret)
        return 'fail'

    # Same with /vsis3_streaming/
    f = open_for_read('/vsis3_streaming/' + s3_resource)
    if f is None:
        gdaltest.post_reason('fail')
        return 'fail'
    ret = gdal.VSIFReadL(1, 1, f)
    gdal.VSIFCloseL(f)

    if len(ret) != 1:
        gdaltest.post_reason('fail')
        print(ret)
        return 'fail'

    # Invalid bucket : "The specified bucket does not exist"
    gdal.ErrorReset()
    f = open_for_read('/vsis3/not_existing_bucket/foo')
    with gdaltest.error_handler():
        gdal.VSIFReadL(1, 1, f)
    gdal.VSIFCloseL(f)
    if gdal.VSIGetLastErrorMsg() == '':
        gdaltest.post_reason('fail')
        print(gdal.VSIGetLastErrorMsg())
        return 'fail'

    # Invalid resource
    gdal.ErrorReset()
    f = open_for_read('/vsis3_streaming/' + gdal.GetConfigOption('S3_RESOURCE') + '/invalid_resource.baz')
    if f is not None:
        gdaltest.post_reason('fail')
        print(gdal.VSIGetLastErrorMsg())
        return 'fail'

    return 'success'

###############################################################################
def vsis3_cleanup():

    for var in gdaltest.aws_vars:
        gdal.SetConfigOption(var, gdaltest.aws_vars[var])

    gdal.SetConfigOption('CPL_AWS_CREDENTIALS_FILE', None)
    gdal.SetConfigOption('AWS_CONFIG_FILE', None)
    gdal.SetConfigOption('CPL_AWS_EC2_CREDENTIALS_URL', None)

    return 'success'

gdaltest_list = [ vsis3_init,
                  vsis3_1,
                  vsis3_start_webserver,
                  vsis3_2,
                  vsis3_3,
                  vsis3_4,
                  vsis3_5,
                  vsis3_6,
                  vsis3_read_credentials_file,
                  vsis3_read_config_file,
                  vsis3_read_credentials_config_file,
                  vsis3_read_credentials_config_file_non_default,
                  vsis3_read_credentials_config_file_inconsistent,
                  vsis3_read_credentials_ec2,
                  vsis3_read_credentials_ec2_expiration,
                  vsis3_stop_webserver,
                  vsis3_cleanup ]

gdaltest_list_extra = [ vsis3_extra_1 ]

if __name__ == '__main__':

    gdaltest.setup_run( 'vsis3' )

    if gdal.GetConfigOption('RUN_MANUAL_ONLY', None):
        gdaltest.run_tests( gdaltest_list_extra )
    else:
        gdaltest.run_tests( gdaltest_list + gdaltest_list_extra + [ vsis3_cleanup ] )

    gdaltest.summarize()
