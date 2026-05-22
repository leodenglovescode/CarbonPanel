import en from './en'
import zh from './zh'

export type Locale = 'en' | 'zh'

export const messages = { en, zh } as const

export type Messages = typeof en

type PathsOf<T, Prefix extends string = ''> = {
  [K in keyof T]: T[K] extends Record<string, unknown>
    ? PathsOf<T[K], `${Prefix}${K & string}.`>
    : `${Prefix}${K & string}`
}[keyof T]

export type TranslationKey = PathsOf<Messages>

export function resolveKey(msgs: Messages, key: string): string {
  const parts = key.split('.')
  let cur: unknown = msgs
  for (const p of parts) {
    if (cur == null || typeof cur !== 'object') return key
    cur = (cur as Record<string, unknown>)[p]
  }
  return typeof cur === 'string' ? cur : key
}
