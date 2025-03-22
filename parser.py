import os
from pathlib import Path
import pandas as pd

################################################################################

def main():
    print(f'Starting...')
    paths = []
    raw_df = pd.DataFrame()

    # Check all subdirectories for outfits
    for root, dirs, files in os.walk('.'):
        for name in files:
            if (
                ('outfits.txt' in name and 'deprecated' not in name) or
                'human\engines.txt' in os.path.join(root, name) or
                'human\power.txt' in os.path.join(root, name) or
                'human\weapons.txt' in os.path.join(root, name)):
                paths.append(os.path.join(root, name))
    raw_df = pd.concat([file_parser(path) for path in paths],
                       join='outer', ignore_index=True)
    print(f'Parsing complete.')

    # Set up dataframes
    raw_df = format_raw(raw_df)
    gp = raw_df.groupby('category')
    dfs = [gp.get_group(g).dropna(axis='columns', how='all') for g in gp.groups]
    root_dict = split_dataframes(dict(zip(gp.groups.keys(), dfs)))
    export(root_dict)
    return

################################################################################

def file_parser(path_str):
    print(f'Current file: {path_str}')
    path = Path(path_str)
    raw_data = []
    data = []
    
    with path.open() as file:
        # Get raw strings from file
        raw_data = map(lambda line: line.strip(), file.readlines())
        it = iter(raw_data)
        
        while (line := next(it, None)) is not None:
            if line.startswith('#') or len(line) <= 0:
                # Exclude comments and empty lines
                True
            else:
                # Pass this line and iterator to function
                outfit = outfit_parser(line, it)
                if outfit is not None:
                    # Skip effects
                    data.append(outfit)
    return pd.DataFrame.from_dict(data)

################################################################################
    
def outfit_parser(line, it):
    data = dict()
    line = line.strip()
    st = ' "'

    # Skip effects
    if line.startswith('effect'):
        while (line := next(it, None)):
            if len(line) <= 0:
                break
        return

    # Handle first line
    key, value = tuple(line.split(' ', 1))
    key, value = key.strip(st), value.strip(st)
    data[key] = value
    
    while (line := next(it, None)) is not None:
        if len(line) <= 0:
            # Stop and return on empty line
            break
        elif (
            # Skip useless attributes
            line.startswith('#') or
            line.startswith('description') or
            line.startswith('"description"') or
            line.startswith('weapon') or
            line.startswith('"rewind"') or
            line.startswith('"random start frame"') or
            line.startswith('"no repeat"') or
            line.startswith('stream') or
            line.startswith('"stream"') or
            line.startswith('cluster') or
            line.startswith('"cluster"') or
            line.startswith('safe') or
            line.startswith('"safe"')):
            continue
        elif line.startswith('licenses'):
            # Skip licenses
            next(it, None)
            continue
        else:
            key = str()
            value = str()
            if line.startswith('"'):
                # Split string after second quotation mark
                index = line.find('"', line.find('"') + 1, -1) + 1
                key, value = line[0:index], line[index - len(line):]
            else:
                # Split string on space
                key, value = tuple(line.split(' ', 1))
            key, value = key.strip(st), value.strip(st)
            data[key] = value
    return data

################################################################################

def format_raw(raw_df):
    useless = ['plural', 'series', 'index', 'thumbnail', '']
    raw_df.drop(useless, axis='columns', inplace=True)
    raw_df = raw_df.convert_dtypes()
    raw_df = raw_df.apply(cast_to_float)
    raw_df['outfit space'] = raw_df['outfit space'] * -1
    raw_df['heat generation'] = raw_df['heat generation'] * 60
    raw_df['energy generation'] = raw_df['energy generation'] * 60
    return raw_df

################################################################################

def cast_to_float(s):
    try:
        return pd.to_numeric(s, downcast='float')
    except:
        return s

################################################################################

def split_dataframes(root_dict):
    # Split "Power" category
    power_sheets = ['Power(Battery)', 'Power(Reactor)', 'Power(Solar)']
    power_dfs = [pd.DataFrame() for i in range(3)]
    power_df = root_dict['Power']

    # Batteries
    move_rows = power_df.loc[power_df['energy capacity'].notnull()]
    power_dfs[0] = pd.concat([move_rows], join='outer', ignore_index=True)
    power_dfs[0] = power_dfs[0].convert_dtypes()
    power_dfs[0].dropna(axis='columns', how='all', inplace=True)
    power_dfs[0]['batt/s'] = \
        power_dfs[0]['energy capacity'] / power_dfs[0]['outfit space']
    
    # Reactors
    move_rows = power_df.loc[power_df['energy generation'].notnull()]
    power_dfs[1] = pd.concat([move_rows], join='outer', ignore_index=True)
    power_dfs[1].dropna(axis='columns', how='all', inplace=True)
    power_dfs[1]['e/s'] = \
        power_dfs[1]['energy generation'] / power_dfs[1]['outfit space']
    power_dfs[1]['e/h'] = \
        power_dfs[1]['energy generation'] / power_dfs[1]['heat generation']

    # Solar
    move_rows = power_df.loc[power_df['solar collection'].notnull()]
    power_dfs[2] = pd.concat([move_rows], join='outer', ignore_index=True)
    power_dfs[2].dropna(axis='columns', how='all', inplace=True)
    power_dfs[2]['sol/s'] = \
        power_dfs[2]['solar collection'] / power_dfs[2]['outfit space']

    # Add subcategory dataframes
    power_dict = dict(zip(power_sheets, power_dfs))
    root_dict.update(power_dict)
    for i in range(3):
        power_df = power_df[~power_df['outfit'].isin(power_dfs[i]['outfit'])]
    root_dict['Power'] = power_df

    return {key: value for key, value in root_dict.items() if not value.empty}

################################################################################

def export(root_dict):
    # Export to xlsx
    with pd.ExcelWriter('outfits.xlsx') as writer:
        for key, value in root_dict.items():
            value.to_excel(writer, sheet_name=key)
    print(f'Write operation complete.')
    return

################################################################################

if __name__ == '__main__':
    main()
