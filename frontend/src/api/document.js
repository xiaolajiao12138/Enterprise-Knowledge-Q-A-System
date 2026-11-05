import request from './request'

export function getDocumentsApi() {
  return request({
    url: '/documents',
    method: 'get'
  })
}

export function uploadDocumentApi(formData) {
  return request({
    url: '/documents/upload',
    method: 'post',
    data: formData,
    headers: {
      'Content-Type': 'multipart/form-data'
    }
  })
}

export function previewDocumentApi(id) {
  return request({
    url: `/documents/${id}/preview`,
    method: 'get'
  })
}

export function downloadDocumentApi(id) {
  return request({
    url: `/documents/${id}/download`,
    method: 'get',
    responseType: 'blob'
  })
}

export function deleteDocumentApi(id) {
  return request({
    url: `/documents/${id}`,
    method: 'delete'
  })
}

export function reindexDocumentApi(id) {
  return request({
    url: `/documents/${id}/reindex`,
    method: 'post'
  })
}

export function getChromaStatsApi() {
  return request({
    url: '/documents/chroma/stats',
    method: 'get'
  })
}

export function clearChromaApi() {
  return request({
    url: '/documents/chroma/clear',
    method: 'post'
  })
}
