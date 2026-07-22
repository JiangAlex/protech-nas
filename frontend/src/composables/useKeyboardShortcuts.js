/**
 * Global keyboard shortcuts for ProTech NAS.
 *
 * Ctrl+K: Focus global search (placeholder for future)
 * Ctrl+U: Navigate to Files (upload)
 * Ctrl+D: Navigate to Dashboard
 */
import { onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'

export function useKeyboardShortcuts() {
  const router = useRouter()

  function handler(e) {
    // Ignore when typing in input/textarea
    const tag = document.activeElement?.tagName?.toLowerCase()
    if (tag === 'input' || tag === 'textarea' || document.activeElement?.isContentEditable) return

    if (e.ctrlKey || e.metaKey) {
      switch (e.key.toLowerCase()) {
        case 'k':
          e.preventDefault()
          // Placeholder: could open a command palette / search
          break
        case 'u':
          e.preventDefault()
          router.push('/files')
          break
        case 'd':
          e.preventDefault()
          router.push('/dashboard')
          break
      }
    }

    // Delete key: could trigger delete in Files view (handled locally)
  }

  onMounted(() => window.addEventListener('keydown', handler))
  onUnmounted(() => window.removeEventListener('keydown', handler))
}
