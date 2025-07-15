import originpro as op
import pandas as pd
import os
import warnings
import numpy as np

# Настройки
input_folder = '.'  # Текущая папка (можно указать другую)
output_file = 'fit_results_varied_max_time.csv'  # Файл для сохранения результатов
initial_time_min = 0  # Фиксированное начальное время
time_range_variations = 5  # Количество вариаций конечного времени
min_points = 10  # Минимальное количество точек для анализа

# Создаем список для хранения результатов
results = []

# Получаем список CSV-файлов в папке
csv_files = [f for f in os.listdir(input_folder) if f.endswith('.csv')]

# Проверяем доступность Origin
if not op.oext:
    raise RuntimeError("Не удалось подключиться к Origin")


def fit_exp_decay(ws, time_range, filename):
    """Функция для выполнения аппроксимации с заданным временным диапазоном"""
    # Аппроксимация ExpDecay1
    fit = op.NLFit('ExpDecay1')
    fit.set_data(ws, 0, 1)  # Столбцы X (0) и Y (1)

    # Установка начальных параметров
    y_data = ws.to_list(1)
    y0_guess = y_data[-1] if len(y_data) > 0 else 0
    A_guess = y_data[0] - y0_guess if len(y_data) > 0 else 1

    # Альтернативные названия параметров
    param_names = {
        'y0': ['y0', 'y0'],
        'A': ['A', 'A1', 'amplitude'],
        't1': ['t1', 'tau1']
    }

    # Пытаемся установить параметры разными способами
    success = False
    for a_name in param_names['A']:
        try:
            fit.parameters = {
                param_names['y0'][0]: y0_guess,
                a_name: A_guess,
                param_names['t1'][0]: 5.0
            }
            fit.fit()
            result = fit.result()
            success = True
            break
        except:
            continue

    if not success:
        return None

    # Получаем результаты
    def get_param(result, names, default=None):
        for name in names:
            if name in result:
                return result[name]
        return default

    t1 = get_param(result, param_names['t1'])
    t1_error = get_param(result, ['e_' + n for n in param_names['t1']])
    A = get_param(result, param_names['A'])
    A_error = get_param(result, ['e_' + n for n in param_names['A']])
    y0 = get_param(result, param_names['y0'])
    y0_error = get_param(result, ['e_' + n for n in param_names['y0']])
    r_squared = result.get('r', 0) ** 2 if 'r' in result else None
    niter = result.get('niter', 0)

    return {
        'Filename': filename,
        't1': t1,
        't1_error': t1_error,
        'y0': y0,
        'y0_error': y0_error,
        'A': A,
        'A_error': A_error,
        'R_squared': r_squared,
        'Iterations': niter,
        'Time_min': time_range[0],
        'Time_max': time_range[1]
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

        # Определяем возможные конечные временные точки
        full_time_max = data['Time (s)'].max()
        time_max_options = np.linspace(full_time_max * 0.3, full_time_max, time_range_variations)

        best_fit = None
        best_r_squared = -1

        # Перебираем все возможные конечные временные точки
        for time_max in time_max_options:
            time_range = (initial_time_min, time_max)
            try:
                # Фильтрация данных
                filtered_data = data[(data['Time (s)'] >= time_range[0]) &
                                     (data['Time (s)'] <= time_range[1])].copy()

                if len(filtered_data) < min_points:
                    continue

                # Загрузка данных в Origin
                op.new_book()
                ws = op.find_sheet()
                ws.from_df(filtered_data)

                # Выполняем аппроксимацию
                current_fit = fit_exp_decay(ws, time_range, filename)

                if current_fit and current_fit['R_squared'] > best_r_squared:
                    best_r_squared = current_fit['R_squared']
                    best_fit = current_fit
                    print(f"Новый лучший R²={best_r_squared:.4f} для диапазона {time_range}")

            except Exception as e:
                warnings.warn(f"Ошибка при анализе диапазона {time_range} для файла {filename}: {str(e)}")
                continue

        if best_fit:
            results.append(best_fit)
            print(
                f"Лучший результат для {filename}: R²={best_r_squared:.4f}, t1={best_fit['t1']:.4f}, диапазон {best_fit['Time_min']:.1f}-{best_fit['Time_max']:.1f}")
        else:
            warnings.warn(f"Не удалось выполнить аппроксимацию для файла {filename}")

    except Exception as e:
        warnings.warn(f"Ошибка при обработке файла {filename}: {str(e)}")

# Сохраняем все результаты в CSV
if results:
    results_df = pd.DataFrame(results)
    # Упорядочиваем столбцы
    cols = ['Filename', 't1', 't1_error', 'A', 'A_error', 'y0', 'y0_error',
            'R_squared', 'Iterations', 'Time_min', 'Time_max']
    results_df = results_df[cols]
    results_df.to_csv(output_file, index=False)
    print(f"\nРезультаты сохранены в {output_file}")
    print(results_df)
else:
    print("\nНе удалось обработать ни один файл")

op.exit()