import originpro as op
import pandas as pd
import os
import warnings
import numpy as np

#Настройки
input_folder = '.'  # Текущая папка
output_file = 'fit_results_fixed_y0_optimized_range.csv'  # Файл для сохранения результатов

# Параметры варьирования временного диапазона
min_time_min = 0  # Минимальное значение начального времени (сек)
max_time_min = 10  # Максимальное значение начального времени (сек)
min_time_max = 30  # Минимальное значение конечного времени (сек)
max_time_max = 119  # Максимальное значение конечного времени (сек)
num_variations = 20# Количество вариантов для time_min и time_max

# Создаем список для хранения результатов
results = []

# Получаем список CSV-файлов в папке
csv_files = [f for f in os.listdir(input_folder) if f.endswith('.csv')]

# Проверяем доступность Origin
if not op.oext:
    raise RuntimeError("Не удалось подключиться к Origin")


def perform_fit(data, time_min, time_max, filename):
    """Выполняет подгонку с фиксированным y0=0 для заданного временного диапазона"""
    # Фильтрация данных
    filtered_data = data[(data['Time (s)'] >= time_min) & (data['Time (s)'] <= time_max)].copy()

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
        'Time_max': time_max,
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

        # Создаем варианты time_min и time_max
        time_min_options = np.linspace(min_time_min, max_time_min, num_variations)
        time_max_options = np.linspace(min_time_max, max_time_max, num_variations)

        best_fit = None
        best_r_squared = -1

        # Перебираем все возможные комбинации time_min и time_max (где time_min < time_max)
        for time_min in time_min_options:
            for time_max in time_max_options:
                if time_min >= time_max:  # Пропускаем случаи, когда time_min >= time_max
                    continue

                try:
                    current_fit = perform_fit(data, time_min, time_max, filename)

                    if current_fit and current_fit['R_squared'] is not None and current_fit[
                        'R_squared'] > best_r_squared:
                        best_r_squared = current_fit['R_squared']
                        best_fit = current_fit
                        print(
                            f"Новый лучший R²={best_r_squared:.4f} при time_min={time_min:.2f}, time_max={time_max:.2f}")

                except Exception as e:
                    warnings.warn(
                        f"Ошибка при time_min={time_min:.2f}, time_max={time_max:.2f} для файла {filename}: {str(e)}")
                    continue

        if best_fit:
            results.append(best_fit)
            print(f"Лучший результат для {filename}:")
            print(f"R² = {best_r_squared:.4f}")
            print(f"t1 = {best_fit['t1']:.4f} ± {best_fit['t1_error']:.4f}")
            print(f"Диапазон = [{best_fit['Time_min']:.2f}-{best_fit['Time_max']:.2f}]")
        else:
            warnings.warn(f"Не удалось выполнить аппроксимацию для файла {filename}")

    except Exception as e:
        warnings.warn(f"Ошибка при обработке файла {filename}: {str(e)}")
    op.exit()

# Сохраняем все результаты в CSV
if results:
    results_df = pd.DataFrame(results)
    # Упорядочиваем столбцы
    cols = ['Filename', 't1', 't1_error', 'A', 'A_error', 'Fixed_y0', 'R_squared',
            'Iterations', 'Time_min', 'Time_max']
    results_df = results_df[cols]
    results_df.to_csv(output_file, index=False)
    print(f"\nРезультаты сохранены в {output_file}")
    print(results_df)
else:
    print("\nНе удалось обработать ни один файл")

op.exit()