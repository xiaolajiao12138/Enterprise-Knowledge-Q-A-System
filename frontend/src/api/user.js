import request from './request'

export function getUsersApi() {
  return request({
    url: '/users',
    method: 'get'
  })
}

export function createUserApi(data) {
  return request({
    url: '/users',
    method: 'post',
    data
  })
}

export function updateUserApi(id, data) {
  return request({
    url: `/users/${id}`,
    method: 'put',
    data
  })
}

export function resetPasswordApi(id, data) {
  return request({
    url: `/users/${id}/reset-password`,
    method: 'post',
    data
  })
}

export function deleteUserApi(id) {
  return request({
    url: `/users/${id}`,
    method: 'delete'
  })
}
