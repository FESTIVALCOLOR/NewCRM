import { computed } from 'vue'
import { usePermissionsStore } from 'src/stores/permissions'

/**
 * Composable для проверки прав.
 * Использование: const { can, isSuperuser } = usePermission()
 * if (can('clients.create')) { ... }
 */
export function usePermission() {
  const perms = usePermissionsStore()

  const isSuperuser = computed(() => perms.isSuperuser)

  function can(permName) {
    return perms.has(permName)
  }

  function canAny(...permNames) {
    return permNames.some(p => perms.has(p))
  }

  return { can, canAny, isSuperuser }
}
