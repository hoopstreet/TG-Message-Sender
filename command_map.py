# Mapping slash commands to their respective logic
CMD_MAP = {
    '/start': start,
    '/status': get_stats_report,
    '/add_list': add_users_handler,
    '/edit_msg': edit_msg_init,
    '/add_account': add_acc_init,
    '/send_now': run_outreach,
    '/pause_send': lambda e: globals().update(IS_SENDING=False)
}
