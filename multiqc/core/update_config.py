import logging
import os
import sys
from pathlib import Path
from typing import Dict, List, Literal, Optional, Union, cast

from pydantic import BaseModel

from multiqc import config, report
from multiqc.core import log_and_rich, plugin_hooks
from multiqc.core.exceptions import RunError
from multiqc.utils.config_schema import AiProviderLiteral

logger = logging.getLogger(__name__)


class ClConfig(BaseModel):
    """
    Holds config updates from the command line or interactive functions.
    """

    file_list: Optional[bool] = None
    prepend_dirs: Optional[bool] = None
    dirs_depth: Optional[int] = None
    fn_clean_sample_names: Optional[bool] = None
    title: Optional[str] = None
    report_comment: Optional[str] = None
    template: Optional[str] = None
    require_logs: Optional[bool] = None
    output_dir: Optional[Union[str, Path]] = None
    use_filename_as_sample_name: Optional[Union[bool, List[str]]] = None
    replace_names: Optional[str] = None
    sample_names: Optional[str] = None
    sample_filters: Optional[str] = None
    filename: Optional[str] = None
    make_data_dir: Optional[bool] = None
    data_format: Optional[str] = None
    zip_data_dir: Optional[bool] = None
    force: Optional[bool] = None
    ignore_symlinks: Optional[bool] = None
    make_report: Optional[bool] = None
    export_plots: Optional[bool] = None
    plots_force_flat: Optional[bool] = None
    plots_force_interactive: Optional[bool] = None
    strict: Optional[bool] = None
    development: Optional[bool] = None
    make_pdf: Optional[bool] = None
    no_megaqc_upload: Optional[bool] = None
    quiet: Optional[bool] = None
    verbose: Optional[bool] = None
    no_ansi: Optional[bool] = None
    profile_runtime: Optional[bool] = None
    profile_memory: Optional[bool] = None
    no_version_check: Optional[bool] = None
    ignore: List[str] = []
    ignore_samples: List[str] = []
    only_samples: List[str] = []
    run_modules: List[str] = []
    exclude_modules: List[str] = []
    config_files: List[Union[str, Path]] = []
    cl_config: List[str] = []
    custom_css_files: List[str] = []
    module_order: List[Union[str, Dict]] = []
    extra_fn_clean_exts: List = []
    extra_fn_clean_trim: List = []
    preserve_module_raw_data: Optional[bool] = None
    data_dump_file_write_raw: Optional[bool] = None
    ai_summary: Optional[bool] = None
    ai_summary_full: Optional[bool] = None
    ai_provider: Optional[AiProviderLiteral] = None
    ai_model: Optional[str] = None
    ai_custom_endpoint: Optional[str] = None
    ai_custom_context_window: Optional[int] = None
    ai_prompt_short: Optional[str] = None
    ai_prompt_full: Optional[str] = None
    no_ai: Optional[bool] = None
    unknown_options: Optional[Dict] = None
    check_config: Optional[bool] = None


def update_config(*analysis_dir, cfg: Optional[ClConfig] = None, log_to_file=False, print_intro_fn=None):
    """
    Update config and re-initialize logger.

    First will reload config from defaults and from the previously added user config files.
    Then will update from cfg from the non-None arguments.
    """

    # Reload from defaults
    config.load_defaults()

    if cfg is None and analysis_dir and isinstance(analysis_dir[0], ClConfig):
        cfg = analysis_dir[0]
    cfg = cfg or ClConfig()

    # Reset logger
    if cfg.quiet is not None:
        config.quiet = cfg.quiet
    if cfg.no_ansi is not None:
        config.no_ansi = cfg.no_ansi
    if cfg.verbose is not None:
        config.verbose = cfg.verbose > 0

    log_and_rich.init_log(log_to_file=log_to_file)
    if print_intro_fn is not None:
        print_intro_fn()

    logger.debug(f"This is MultiQC v{config.version}")
    logger.debug("Running Python " + sys.version.replace("\n", " "))

    plugin_hooks.mqc_trigger("before_config")

    config.loaded_user_files = set()

    # Re-finding implicit configs
    config.find_user_files()

    # Re-loading explicit user configs
    path: Union[Path, str]
    for path in config.explicit_user_config_files:
        config.load_config_file(path)

    # Set up session config files passed with -c or cfg=
    for path in cfg.config_files:
        config.load_config_file(str(path), is_explicit_config=False)

    # Command-line config YAML
    if len(cfg.cl_config) > 0:
        config.load_cl_config(cfg.cl_config)

    # Set up key variables (overwrite config vars from command line)
    if cfg.template is not None:
        config.template = cfg.template
    if cfg.title is not None:
        config.title = cfg.title
        logger.info(f"Report title: {config.title}")
    if cfg.report_comment is not None:
        config.report_comment = cfg.report_comment
    if cfg.prepend_dirs is not None:
        config.prepend_dirs = cfg.prepend_dirs
        logger.info("Prepending directory to sample names")
    if cfg.dirs_depth is not None:
        config.prepend_dirs = True
        config.prepend_dirs_depth = cfg.dirs_depth
    if cfg.output_dir is not None:
        config.output_dir = os.path.realpath(cfg.output_dir)
    if cfg.use_filename_as_sample_name is not None:
        config.use_filename_as_sample_name = cfg.use_filename_as_sample_name
        if cfg.use_filename_as_sample_name:
            logger.info("Using log filenames for sample names")
    if cfg.make_data_dir is not None:
        config.make_data_dir = cfg.make_data_dir
    if cfg.force is not None:
        config.force = cfg.force
    if cfg.ignore_symlinks is not None:
        config.ignore_symlinks = cfg.ignore_symlinks
    if cfg.zip_data_dir is not None:
        config.zip_data_dir = cfg.zip_data_dir
    if cfg.data_format is not None:
        config.data_format = cfg.data_format
    if cfg.export_plots is not None:
        config.export_plots = cfg.export_plots
    if cfg.make_report is not None:
        config.make_report = cfg.make_report
    if cfg.plots_force_flat is not None:
        config.plots_force_flat = cfg.plots_force_flat
    if cfg.plots_force_interactive is not None:
        config.plots_force_interactive = cfg.plots_force_interactive
    if cfg.strict is not None:
        config.strict = cfg.strict
        config.lint = cfg.strict  # Deprecated since v1.17
    if cfg.development is not None:
        config.development = cfg.development
    if cfg.make_pdf:
        config.make_pdf = cfg.make_pdf
        config.template = "simple"
    if config.template == "simple":
        config.plots_force_flat = True
        config.simple_output = True
    if cfg.filename:
        config.filename = cfg.filename
    if cfg.no_megaqc_upload is not None:
        config.megaqc_upload = not cfg.no_megaqc_upload
    if cfg.fn_clean_sample_names is not None:
        config.fn_clean_sample_names = cfg.fn_clean_sample_names
        logger.info("Not cleaning sample names")
    if cfg.replace_names:
        config.load_replace_names(Path(cfg.replace_names))
    if cfg.sample_names:
        config.load_sample_names(Path(cfg.sample_names))
    config.load_show_hide(show_hide_file=Path(cfg.sample_filters) if cfg.sample_filters else None)
    if len(cfg.run_modules) > 0:
        config.run_modules = cfg.run_modules
    if len(cfg.exclude_modules) > 0:
        config.exclude_modules = cfg.exclude_modules
    if cfg.require_logs is not None:
        config.require_logs = cfg.require_logs
    if cfg.profile_runtime is not None:
        config.profile_runtime = cfg.profile_runtime
    if cfg.profile_memory is not None:
        config.profile_runtime = config.profile_memory = cfg.profile_memory
    if cfg.no_version_check is not None:
        config.no_version_check = cfg.no_version_check
    if cfg.custom_css_files:
        config.custom_css_files.extend(cfg.custom_css_files)
    if cfg.module_order:
        config.module_order = cfg.module_order
    if cfg.extra_fn_clean_exts:
        config.fn_clean_exts = list(cfg.extra_fn_clean_exts) + config.fn_clean_exts
    if cfg.extra_fn_clean_trim:
        config.fn_clean_trim = list(cfg.extra_fn_clean_trim) + config.fn_clean_trim
    if cfg.preserve_module_raw_data is not None:
        config.preserve_module_raw_data = cfg.preserve_module_raw_data
    if cfg.data_dump_file_write_raw is not None:
        config.data_dump_file_write_raw = cfg.data_dump_file_write_raw
    if cfg.ai_summary is not None:
        config.ai_summary = cfg.ai_summary
    if cfg.ai_summary_full is not None:
        config.ai_summary = cfg.ai_summary_full
        config.ai_summary_full = cfg.ai_summary_full
    if cfg.ai_provider is not None:
        config.ai_provider = cfg.ai_provider
    if cfg.ai_model is not None:
        config.ai_model = cfg.ai_model
    if cfg.ai_custom_endpoint is not None:
        config.ai_custom_endpoint = cfg.ai_custom_endpoint
    if cfg.ai_custom_context_window is not None:
        config.ai_custom_context_window = cfg.ai_custom_context_window
    if cfg.ai_prompt_short is not None:
        config.ai_prompt_short = cfg.ai_prompt_short
    if cfg.ai_prompt_full is not None:
        config.ai_prompt_full = cfg.ai_prompt_full
    if cfg.no_ai is not None:
        config.no_ai = cfg.no_ai

    if config.development and "png" not in config.export_plot_formats:
        config.export_plot_formats.append("png")

    # Clean up analysis_dir if a string (interactive environment only)
    if analysis_dir:
        config.analysis_dir = [p for p in analysis_dir]
    if cfg.file_list is not None:
        if len(config.analysis_dir) > 1:
            raise RunError("If --file-list is given, analysis_dir should have only one plain text file.")
        config.file_list = cfg.file_list

    if len(cfg.ignore) > 0:
        logger.debug(f"Ignoring files, directories and paths that match: {', '.join(cfg.ignore)}")
        config.fn_ignore_files.extend(cfg.ignore)
        config.fn_ignore_dirs.extend(cfg.ignore)
        config.fn_ignore_paths.extend(cfg.ignore)
    if len(cfg.ignore_samples) > 0:
        logger.debug(f"Ignoring sample names that match: {', '.join(cfg.ignore_samples)}")
        config.sample_names_ignore.extend(cfg.ignore_samples)
    if len(cfg.only_samples) > 0:
        logger.debug(f"Only including sample names that match: {', '.join(cfg.only_samples)}")
        config.sample_names_only_include.extend(cfg.only_samples)
    # Prep module configs
    report.top_modules = [m if isinstance(m, dict) else {m: {}} for m in config.top_modules]
    report.module_order = [m if isinstance(m, dict) else {m: {}} for m in config.module_order]

    if cfg.unknown_options:
        config.kwargs = cfg.unknown_options  # plug in command line options

    plugin_hooks.mqc_trigger("config_loaded")
    plugin_hooks.mqc_trigger("execution_start")
