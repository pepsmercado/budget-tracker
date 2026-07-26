const quotes = [
  { text: "Do not save what is left after spending, but spend what is left after saving.", author: "Warren Buffett" },
  { text: "A budget is telling your money where to go instead of wondering where it went.", author: "Dave Ramsey" },
  { text: "Beware of little expenses; a small leak will sink a great ship.", author: "Benjamin Franklin" },
  { text: "It's not about how much money you make, but how much money you keep.", author: "Robert Kiyosaki" },
  { text: "Money is a terrible master but an excellent servant.", author: "P.T. Barnum" },
  { text: "The best time to plant a tree was 20 years ago. The second best time is now.", author: "Chinese Proverb" },
  { text: "Spend your money on things that save you time.", author: "Naval Ravikant" },
  { text: "Price is what you pay. Value is what you get.", author: "Warren Buffett" },
  { text: "Every time you borrow money, you're robbing your future self.", author: "Nathan W. Morris" },
  { text: "Rich people stay rich by living like they're poor. Poor people stay poor by living like they're rich." },
  { text: "Don't tell me where your priorities are. Show me where you spend your money.", author: "James W. Frick" },
  { text: "Financial freedom is available to those who learn about it and work for it.", author: "Robert Kiyosaki" },
  { text: "This week's budget check-in: you're doing better than you think." },
  { text: "Small changes lead to big results. Keep going." },
  { text: "The goal isn't more money. The goal is living life on your own terms.", author: "Chris Brogan" },
]

export const QUOTE_COUNT = quotes.length

const WEEK_MS = 7 * 24 * 60 * 60 * 1000

export function getWeeklyIndex() {
  return Math.floor(Date.now() / WEEK_MS) % QUOTE_COUNT
}

export function getQuoteAt(index) {
  return quotes[((index % QUOTE_COUNT) + QUOTE_COUNT) % QUOTE_COUNT]
}
