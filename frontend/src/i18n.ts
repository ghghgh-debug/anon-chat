import { ref } from 'vue'

export type AppLanguage = 'ru' | 'en' | 'uz'
export const appLanguage = ref<AppLanguage>((localStorage.getItem('app_language') as AppLanguage) || 'ru')

const copy = {
  ru: { chooseLanguage: 'Выберите язык приложения', continue: 'Продолжить', chatLanguage: 'Язык чата', topics: 'Темы разговора', games: 'Игры: /пд, /яникогда, /выбор', hint: 'Можно начать с вопроса', save: 'Сохранить', language: 'Язык приложения' },
  en: { chooseLanguage: 'Choose app language', continue: 'Continue', chatLanguage: 'Chat language', topics: 'Conversation topics', games: 'Games: /pd, /never, /wouldyou', hint: 'Start with a question', save: 'Save', language: 'App language' },
  uz: { chooseLanguage: 'Ilova tilini tanlang', continue: 'Davom etish', chatLanguage: 'Chat tili', topics: 'Suhbat mavzulari', games: "O'yinlar: /pd, /never, /wouldyou", hint: 'Savol bilan boshlang', save: 'Saqlash', language: 'Ilova tili' },
} as const

export function setAppLanguage(language: AppLanguage) {
  appLanguage.value = language
  localStorage.setItem('app_language', language)
}

export function t(key: keyof typeof copy.ru) { return copy[appLanguage.value][key] }

export const topicOptions = [
  { id: 'talk', icon: '💬', ru: 'Общение', en: 'Chatting', uz: 'Suhbat' },
  { id: 'flirt', icon: '💕', ru: 'Флирт', en: 'Flirting', uz: 'Flirt' },
  { id: 'photos', icon: '📷', ru: 'Обмен фото', en: 'Photo exchange', uz: 'Rasm almashish' },
  { id: 'games', icon: '🎮', ru: 'Игры', en: 'Games', uz: "O'yinlar" },
  { id: 'music', icon: '🎵', ru: 'Музыка', en: 'Music', uz: 'Musiqa' },
  { id: 'movies', icon: '🎬', ru: 'Кино и сериалы', en: 'Movies & shows', uz: 'Kino va seriallar' },
  { id: 'dating', icon: '✨', ru: 'Знакомства', en: 'Dating', uz: 'Tanishuv' },
  { id: 'confessions', icon: '🤫', ru: 'Откровенно', en: 'Confessions', uz: 'Sirli suhbat' },
  { id: 'travel', icon: '✈️', ru: 'Путешествия', en: 'Travel', uz: 'Sayohat' },
  { id: 'memes', icon: '😂', ru: 'Мемы и юмор', en: 'Memes & humour', uz: 'Memlar va hazil' },
]
