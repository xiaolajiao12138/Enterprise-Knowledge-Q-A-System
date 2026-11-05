import request from './request'

export function loginApi(data) {
  return request({
    url: '/auth/login',
    method: 'post',
    data
  })
}

export function getMeApi() {
  return request({
    url: '/auth/me',
    method: 'get'
  })
}

export function logoutApi() {
  return request({
    url: '/auth/logout',
    method: 'post'
  })
}
