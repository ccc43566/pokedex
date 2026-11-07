import visitors from '../assets/night/visitors.json'

export type NightVisitor = (typeof visitors)[number]
export { visitors as nightVisitors }

export function nightVisitorName(visitor: NightVisitor, locale: string): string {
  return locale === 'zh-Hans' ? visitor.name : visitor.englishName
}

export function nightVisitorStyle(visitor: NightVisitor): Record<string, string> {
  const animation = visitor.animation
  if (!animation) return {}
  const scale = Math.min(1, 96 / Math.max(animation.width, animation.height))
  return {
    '--animated-width': `${((animation.width * scale) / 96) * 100}%`,
    '--animated-height': `${((animation.height * scale) / 96) * 100}%`,
  }
}
