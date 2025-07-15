import originpro as op
import pandas as pd
import os
import warnings
import numpy as np

# Настройки
input_folder = '.'  # Текущая папка
output_file = 'fit_results_fixed_y0_optimized.csv'  # Файл для сохранения результатов
min_time_range = 0  # Минимальное время (сек)
max_time_range = 15  # Максимальное время для варьирования
num_variations = 20  # Количество вариантов time_min для проверки

# Создаем список для хранения результатов
results = []

# Получаем список CSV-файлов в папке
csv_files = [f for f in os.listdir(input_folder) if f.endswith('.csv')]

# Проверяем доступность Origin
if not op.oext:
    raise RuntimeError("Не удалось подключиться к Origin")


def perform_fit(data, time_min, filename):
    """Выполняет подгонку с фиксированным y0=0 для заданного time_min"""
    # Фильтрация данных
    filtered_data = data[data['Time (s)'] >= time_min].copy()

    if len(filtered_data) < 10:
        return None

    # Загрузка данных в Origin
    op.new_book()
    ws = op.find_sheet()
    ws.from_df(filtered_data)

    # Аппроксимация ExpDecay1 с фиксированным y0=0
    fit = op.NLFit('ExpDecay1')
    fit.set_data(ws, 0, 1)

    # Установка начальных параметров
    A_guess = filtered_data.iloc[0, 1] - 0  # y0 фиксирован как 0

    # Параметры могут называться по-разному в разных версиях Origin
    param_names = {
        'A': ['A', 'A1', 'amplitude'],
        't1': ['t1', 'tau1']
    }

    # Пытаемся установить параметры
    success = False
    for a_name in param_names['A']:
        try:
            fit.parameters = {
                a_name: A_guess,
                param_names['t1'][0]: 5.0
            }
            fit.fix_param('y0', 0)  # Фиксируем y0=0
            fit.fit()
            result = fit.result()
            success = True
            break
        except Exception as e:
            continue

    if not success:
        return None

    # Функция для безопасного извлечения параметров
    def get_param(result, names, default=None):
        for name in names:
            if name in result:
                return result[name]
        return default

    t1 = get_param(result, param_names['t1'])
    t1_error = get_param(result, ['e_' + n for n in param_names['t1']])
    A = get_param(result, param_names['A'])
    A_error = get_param(result, ['e_' + n for n in param_names['A']])
    r_squared = result.get('r', 0) ** 2 if 'r' in result else None
    niter = result.get('niter', 0)

    return {
        'Filename': filename,
        't1': t1,
        't1_error': t1_error,
        'A': A,
        'A_error': A_error,
        'R_squared': r_squared,
        'Iterations': niter,
        'Time_min': time_min,
        'Fixed_y0': 0
    }


# Обрабатываем каждый файл
for filename in csv_files:
    try:
        print(f"\nОбработка файла: {filename}")

        # Чтение данных
        data = pd.read_csv(os.path.join(input_folder, filename))

        # Проверяем наличие нужных столбцов
        if 'Time (s)' not in data.columns or len(data.columns) < 2:
            warnings.warn(f"Файл {filename} не содержит нужных столбцов. Пропускаем.")
            continue

        # Создаем варианты time_min от 2 до 15 секунд
        time_min_options = np.linspace(min_time_range, max_time_range, num_variations)

        best_fit = None
        best_r_squared = -1

        for time_min in time_min_options:
            try:
                current_fit = perform_fit(data, time_min, filename)

                if current_fit and current_fit['R_squared'] > best_r_squared:
                    best_r_squared = current_fit['R_squared']
                    best_fit = current_fit
                    print(f"Новый лучший R²={best_r_squared:.4f} при time_min={time_min:.2f}")

            except Exception as e:
                warnings.warn(f"Ошибка при time_min={time_min:.2f} для файла {filename}: {str(e)}")
                continue

        if best_fit:
            results.append(best_fit)
            print(
                f"Лучший результат для {filename}: R²={best_r_squared:.4f}, t1={best_fit['t1']:.4f}, time_min={best_fit['Time_min']:.2f}")
        else:
            warnings.warn(f"Не удалось выполнить аппроксимацию для файла {filename}")

    except Exception as e:
        warnings.warn(f"Ошибка при обработке файла {filename}: {str(e)}")

# Сохраняем все результаты в CSV
if results:
    results_df = pd.DataFrame(results)
    # Упорядочиваем столбцы
    cols = ['Filename', 't1', 't1_error', 'A', 'A_error', 'Fixed_y0', 'R_squared', 'Iterations', 'Time_min']
    results_df = results_df[cols]
    results_df.to_csv(output_file, index=False)
    print(f"\nРезультаты сохранены в {output_file}")
    print(results_df)
else:
    print("\nНе удалось обработать ни один файл")

op.exit()