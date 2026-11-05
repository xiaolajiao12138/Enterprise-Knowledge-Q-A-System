import request from './request'

export function getSystemConfigApi() {
  return request({
    url: '/settings',
    method: 'get'
  })
}

export function updateSystemConfigApi(data) {
  return request({
    url: '/settings',
    method: 'put',
    data
  })
}

export function testModelConnectionApi(data) {
  return request({
    url: '/settings/test-model',
    method: 'post',
    data
  })
}

export function getSystemLogsApi(params) {
  return request({
    url: '/settings/logs',
    method: 'get',
    params
  })
}
