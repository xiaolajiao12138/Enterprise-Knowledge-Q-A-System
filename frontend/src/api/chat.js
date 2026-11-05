import request from './request'

export function getSessionsApi() {
  return request({
    url: '/chat/sessions',
    method: 'get'
  })
}

export function createSessionApi(data = { title: '新对话' }) {
  return request({
    url: '/chat/sessions',
    method: 'post',
    data
  })
}

export function renameSessionApi(id, data) {
  return request({
    url: `/chat/sessions/${id}`,
    method: 'put',
    data
  })
}

export function deleteSessionApi(id) {
  return request({
    url: `/chat/sessions/${id}`,
    method: 'delete'
  })
}

export function clearSessionMessagesApi(id) {
  return request({
    url: `/chat/sessions/${id}/clear`,
    method: 'post'
  })
}

export function getSessionMessagesApi(id) {
  return request({
    url: `/chat/sessions/${id}/messages`,
    method: 'get'
  })
}

export function askQuestionApi(data) {
  return request({
    url: '/chat/ask',
    method: 'post',
    data
  })
}

export function exportChatHistoryApi(sessionId) {
  const url = sessionId ? `/chat/export?session_id=${sessionId}` : '/chat/export'
  return request({
    url,
    method: 'get',
    responseType: 'blob'
  })
}
