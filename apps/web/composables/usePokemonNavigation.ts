import type { DetailTarget } from '~/utils/detailNavigation'
import { relatedDetailLocation, safeReturnPath } from '~/utils/detailNavigation'

export function usePokemonNavigation(compact: () => boolean = () => false) {
  const route = useRoute()
  const router = useRouter()
  const localePath = useLocalePath()
  function relatedLocation(target: DetailTarget) {
    return relatedDetailLocation(
      route,
      target,
      compact(),
      localePath(`/pokemon/${target.pokemonId}`),
    )
  }
  function fullPageLocation(id: string) {
    return {
      path: localePath(`/pokemon/${id}`),
      query: { from: route.fullPath, form: route.query.form },
    }
  }
  return {
    relatedLocation,
    select: (target: DetailTarget) => router.push(relatedLocation(target)),
    fullPageLocation,
    returnTo: computed(() => safeReturnPath(route.query.from) || localePath('/pokemon')),
  }
}
