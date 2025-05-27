#!/usr/bin/env python3

"""
Process bylaws JSON file and enrich with status data from auxiliary JSON files.
"""

import argparse
import json
import os
import sys

def load_json_file(path):
    """
    Load JSON data from a file. Return an empty list if the file is not found.
    Exit on other errors.
    """
    try:
        with open(path, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return []
    except json.JSONDecodeError as e:
        print(f"Error decoding JSON from {path}: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error reading {path}: {e}", file=sys.stderr)
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="Process bylaws file and merge status info.")
    parser.add_argument('input_file', help="Path to main bylaws JSON file")
    args = parser.parse_args()

    input_file = args.input_file
    base, ext = os.path.splitext(input_file)
    if ext.lower() != '.json':
        print("Error: Input file must have a .json extension", file=sys.stderr)
        sys.exit(1)

    # Define auxiliary file paths
    aux_files = {
        'not_active_only': f"{base}.NOT_ACTIVE_ONLY.json",
        'revoked':            f"{base}.REVOKED.json",
        'active_only':        f"{base}.ACTIVE_ONLY.json",
        'processed_for_rev':  f"{base}.PROCESSED_FOR_REVOCATION.json",
    }

    # Load main bylaws data
    try:
        with open(input_file, 'r') as f:
            main_data = json.load(f)
    except Exception as e:
        print(f"Error reading main input file {input_file}: {e}", file=sys.stderr)
        sys.exit(1)

    # Load auxiliary lists
    not_active_list         = load_json_file(aux_files['not_active_only'])
    revoked_list            = load_json_file(aux_files['revoked'])
    active_only_list        = load_json_file(aux_files['active_only'])
    processed_for_rev_list  = load_json_file(aux_files['processed_for_rev'])

    # Build lookup structures
    not_active_map  = {item['bylawNumber']: item for item in not_active_list if 'bylawNumber' in item}
    revoked_map     = {item['bylawNumber']: item for item in revoked_list if 'bylawNumber' in item}
    active_set      = {item['bylawNumber'] for item in active_only_list if 'bylawNumber' in item}
    processed_set   = {item['bylawNumber'] for item in processed_for_rev_list if 'bylawNumber' in item}

    output_data = []
    summary = {
        'total': len(main_data),
        'not_active_only': [],
        'revoked': [],
        'active_only': [],
        'processed_for_revocation': [],
        'errors': []
    }

    # Process each bylaw
    for record in main_data:
        bn = record.get('bylawNumber')
        if not bn:
            print("Skipping record without 'bylawNumber'", file=sys.stderr)
            summary['errors'].append("<missing bylawNumber>")
            continue

        enriched = dict(record)
        if bn in not_active_map:
            enriched['isActive'] = not_active_map[bn].get('isActive')
            enriched['whyNotActive'] = not_active_map[bn].get('whyNotActive')
            summary['not_active_only'].append(bn)
        elif bn in revoked_map:
            enriched['isActive'] = revoked_map[bn].get('isActive')
            enriched['whyNotActive'] = revoked_map[bn].get('whyNotActive')
            summary['revoked'].append(bn)
        elif bn in active_set or bn in processed_set:
            enriched['isActive'] = True
            enriched['whyNotActive'] = None
            if bn in active_set:
                summary['active_only'].append(bn)
            else:
                summary['processed_for_revocation'].append(bn)
        else:
            print(f"Error: Bylaw number {bn} not found in auxiliary files", file=sys.stderr)
            summary['errors'].append(bn)
            enriched['isActive'] = None
            enriched['whyNotActive'] = None

        output_data.append(enriched)

    # Write output file
    output_file = f"{base}.FOR_DB.json"
    try:
        with open(output_file, 'w') as f:
            json.dump(output_data, f, indent=2)
        print(f"Output written to {output_file}")
    except Exception as e:
        print(f"Error writing to output file {output_file}: {e}", file=sys.stderr)
        sys.exit(1)

    # Print summary
    print("\nSummary:")
    print(f"Total bylaws processed: {summary['total']}")
    print(f"Found in NOT_ACTIVE_ONLY: {len(summary['not_active_only'])} -> {summary['not_active_only']}")
    print(f"Found in REVOKED: {len(summary['revoked'])} -> {summary['revoked']}")
    print(f"Found in ACTIVE_ONLY: {len(summary['active_only'])} -> {summary['active_only']}")
    print(f"Found in PROCESSED_FOR_REVOCATION: {len(summary['processed_for_revocation'])} -> {summary['processed_for_revocation']}")
    print(f"Errors (not found in auxiliary files): {len(summary['errors'])} -> {summary['errors']}")

if __name__ == "__main__":
    main()
