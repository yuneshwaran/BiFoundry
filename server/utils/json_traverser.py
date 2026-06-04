def deep_traverse(obj, path=""):
    results = []

    if isinstance(obj, dict):
        for k, v in obj.items():
            new_path = f"{path}.{k}" if path else k
            results.append((new_path, v))
            results.extend(deep_traverse(v, new_path))

    elif isinstance(obj, list):
        for i, item in enumerate(obj):
            new_path = f"{path}[{i}]"
            results.append((new_path, item))
            results.extend(deep_traverse(item, new_path))

    return results