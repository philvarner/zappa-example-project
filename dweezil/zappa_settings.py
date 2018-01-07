def generate_zappa_settings(*, template, region,
                            queue_name_prefix, resource_suffix, username):
    with open(template, 'r') as f:
        template_str = f.read()

    return template_str.format(region=region,
                               queue_name_prefix=queue_name_prefix,
                               resource_suffix=resource_suffix,
                               username=username)
