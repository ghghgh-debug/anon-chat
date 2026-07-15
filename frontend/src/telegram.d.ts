interface TelegramWebApp {
  initData: string
  openInvoice(url: string, callback: (status: string) => void): void
}

interface Window {
  Telegram?: { WebApp?: TelegramWebApp }
}
