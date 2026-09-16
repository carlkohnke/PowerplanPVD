% Capture the unmodified legacy script's numerical workspace.
% Inputs are supplied as environment variables so the legacy script may
% execute its initial `clear` without deleting paths needed by this wrapper.

source_dir = getenv('SPUTTERPLAN_SOURCE_DIR');
output_mat = getenv('SPUTTERPLAN_BASELINE_MAT');
output_plot = getenv('SPUTTERPLAN_BASELINE_PLOT');

if isempty(source_dir) || isempty(output_mat)
    error('SPUTTERPLAN_SOURCE_DIR and SPUTTERPLAN_BASELINE_MAT are required.');
end

set(groot, 'defaultFigureVisible', 'off');
cd(source_dir);

tic;
run('Sputtering_Operation_Plan_Maker.m');
matlab_runtime_seconds = toc;

% The legacy script starts with `clear`, so reload wrapper paths afterward.
output_mat = getenv('SPUTTERPLAN_BASELINE_MAT');
output_plot = getenv('SPUTTERPLAN_BASELINE_PLOT');

if ~isempty(output_plot)
    exportgraphics(gcf, output_plot, 'Resolution', 160);
end

save(output_mat, 'L', 'x', 'dx', 'dL', 'k_solved', 'dt', 't', ...
    'power', 'RampRate', 'RAMP_RATE', 'POWER', 'Ktest', 'xtest', ...
    'ImportantIndices', 'II', 'important', 'names', 'K', ...
    'one_constant', 'constant_power_chamber', 'one_power', ...
    'total_power', 'tolerance', 'matlab_runtime_seconds', '-v7');

fprintf('Saved MATLAB baseline to %s\n', output_mat);
