import { employeesApi } from 'src/services/api'

const _cache = {
  byId: {},
  byName: {},
  loaded: false,
  promise: null,
}

export function useEmployeeAvatars() {
  function ensureLoaded() {
    if (_cache.loaded) return Promise.resolve()
    if (_cache.promise) return _cache.promise
    _cache.promise = employeesApi
      .getList({ skip: 0, limit: 500 })
      .then(({ data }) => {
        const list = Array.isArray(data) ? data : data.items || []
        for (const emp of list) {
          if (emp.photo_url) {
            if (emp.id) _cache.byId[emp.id] = emp.photo_url
            if (emp.full_name) _cache.byName[emp.full_name] = emp.photo_url
          }
        }
        _cache.loaded = true
        _cache.promise = null
      })
      .catch(() => {
        _cache.promise = null
      })
    return _cache.promise
  }

  function getAvatarById(id) {
    if (!id) return null
    return _cache.byId[id] || null
  }

  function getAvatarByName(name) {
    if (!name) return null
    return _cache.byName[name] || null
  }

  return { ensureLoaded, getAvatarById, getAvatarByName }
}
