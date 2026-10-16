# Справочник команды

General Manager создаёт сессии ролей сам и вписывает сюда их адреса (`session_id`) и короткие имена. Сообщения — инструментом отправки сообщения в другую сессию.

| Роль | Адрес сессии | При проблеме пишет |
|---|---|---|
| General Manager | | Владельцу |
| Manager | | General Manager |
| Senior Developer | | Manager; права — DevOps |
| Middle Developer | | Manager; права — DevOps |
| Architect | | Manager |
| Auditor | | ВОЗВРАТ — исполнителю, ПРИНЯТО — Manager, СПОР — General Manager |
| Head of Security | | General Manager; права — владельцу |
| DevOps | | Head of Security |
| Analyst | | Manager |
| Releaser | | Head of Security; что записывать — Manager |

## Регламент

1. Проблема — сразу сообщение наверх; журнал дополнительно.
2. Нет ответа 15 минут — на ступень выше.
3. Пауза рассылки («Paused until your user's next message») — сообщение в `team/outbox/OUTBOX-<роль>.md`; будильник роли отправит.
