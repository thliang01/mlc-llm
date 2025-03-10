"""The Python API for MLC chat."""
#! pylint: disable=unused-import, invalid-name
import ctypes
import json
import os
import sys
from dataclasses import dataclass, fields, asdict
from enum import Enum
from typing import List, Optional

import tvm
import tvm._ffi.base

from . import libinfo, callback

# pylint: disable=line-too-long
_PYTHON_GET_STARTED_TUTORIAL_URL = "https://github.com/mlc-ai/notebooks/blob/main/mlc-llm/tutorial_chat_module_getting_started.ipynb"
# pylint: enable=line-too-long


def _load_mlc_llm_lib():
    """Load mlc llm lib"""
    if sys.platform.startswith("win32") and sys.version_info >= (3, 8):
        for path in libinfo.get_dll_directories():
            os.add_dll_directory(path)
    lib_name = "mlc_llm" if tvm._ffi.base._RUNTIME_ONLY else "mlc_llm_module"
    lib_path = libinfo.find_lib_path(lib_name, optional=False)
    return ctypes.CDLL(lib_path[0]), lib_path[0]


# only load once here
if os.environ.get("SKIP_LOADING_MLCLLM_SO", "0") == "0":
    _LIB, _LIB_PATH = _load_mlc_llm_lib()


def quantization_keys():
    return [
        "autogptq_llama_q4f16_0",
        "q0f16",
        "q0f32",
        "q3f16_0",
        "q3f16_1",
        "q4f16_0",
        "q4f16_1",
        "q4f16_ft",
        "q4f32_0",
        "q4f32_1",
        "q8f16_0",
        "q8f16_ft",
    ]


@dataclass
class ConvConfig:
    r"""A dataclass that represents user-defined partial configuration for conversation template.

    This is an attribute of :class:`mlc_chat.ChatConfig`, which can then be passed in to the
    instantiation of a :class:`mlc_chat.ChatModule` instance to override the default
    setting in ``mlc-chat-config.json`` under the model folder. Note that we will
    first load the predefined template with the name specified in ``conv_template``.

    Since the configuration is partial, everything will be ``Optional``.

    Parameters
    ----------
    name : Optional[str]
        Name of the conversation.
    system : Optional[str]
        The prompt encoded before starting the chat.
    roles : Optional[List[str]]
        An array that describes the role names of the user and the model. These
        names are specific to the model being used.
    messages : Optional[List[str]]
        The chat history represented as an array of string pairs in the following
        format: ``[[role_0, msg_0], [role_1, msg_1], ...]``.
    offset : Optional[str]
        The offset used to begin the chat from the chat history. When offset
        is not ``0``, ``messages[0:offset-1]`` will be encoded.
    separator_style : Optional[int]
        Specifies whether we are in chat-bot mode (``0``) or pure LM prompt mode (``1``).
    seps : Optional[List[str]]
        An array of strings indicating the separators to be used after a user
        message and a model message respectively.
    role_msg_sep : Optional[str]
        A string indicating the separator between a role and a message.
    role_empty_sep : Optional[str]
        A string indicating the separator to append to a role when there is no message yet.
    stop_str : Optional[str]
        When the ``stop_str`` is encountered, the model will stop generating output.
    stop_tokens : Optional[List[int]]
        A list of token IDs that act as stop tokens.
    add_bos : Optional[bool]
        Determines whether a beginning-of-string (bos) token should be added
        before the input tokens.
    """

    name: Optional[str] = None
    system: Optional[str] = None
    roles: Optional[List[str]] = None
    messages: Optional[List[str]] = None
    offset: Optional[str] = None
    separator_style: Optional[int] = None
    seps: Optional[List[str]] = None
    role_msg_sep: Optional[str] = None
    role_empty_sep: Optional[str] = None
    stop_str: Optional[str] = None
    stop_tokens: Optional[List[int]] = None
    add_bos: Optional[bool] = None


@dataclass
class ChatConfig:
    r"""A dataclass that represents user-defined partial configuration for the
    chat config file.

    An instance of ``ChatConfig`` can be passed in to the instantiation of a
    :class:`mlc_chat.ChatModule` instance to override the default setting in
    ``mlc-chat-config.json`` under the model folder.

    Since the configuraiton is partial, everything will be ``Optional``.

    Note that we will exploit this class to also represent ``mlc-chat-config.json``
    during intermediate processing.

    Parameters
    ----------
    model_lib : Optional[str]
        The necessary model library to launch this model architecture. We recommend
        reuse model library when possible. For example, all LLaMA-7B models can
        use ``vicuna-v1-7b-{matching quantization scheme}``. So you can distribute
        LLaMA-7B weight variants and still use them in prebuilt MLC chat apps.
    local_id : Optional[str]
        Uniquely identifying the model in application. This is also used by
        command line interface app to specify which model to run.
    conv_template : Optional[str]
        The name of the conversation template that this chat uses.
    temperature : Optional[float]
        The temperature applied to logits before sampling. The default value is
        ``0.7``. A higher temperature encourages more diverse outputs, while a
        lower temperature produces more deterministic outputs.
    repetition_penalty : Optional[float]
        The repetition penalty controls the likelihood of the model generating
        repeated texts. The default value is set to ``1.0``, indicating that no
        repetition penalty is applied. Increasing the value reduces the
        likelihood of repeat text generation. However, setting a high
        ``repetition_penalty`` may result in the model generating meaningless
        texts. The ideal choice of repetition penalty may vary among models.

        For more details on how repetition penalty controls text generation, please
        check out the CTRL paper (https://arxiv.org/pdf/1909.05858.pdf).
    top_p : Optional[float]
        This parameter determines the set of tokens from which we sample during
        decoding. The default value is set to ``0.95``. At each step, we select
        tokens from the minimal set that has a cumulative probability exceeding
        the ``top_p`` parameter.

        For additional information on top-p sampling, please refer to this blog
        post: https://huggingface.co/blog/how-to-generate#top-p-nucleus-sampling.
    mean_gen_len : Optional[int]
    max_gen_len : Optional[int]
    shift_fill_factor : Optional[float]
    tokenizer_files : Optional[List[str]]
        List of tokenizer files of the model.
    conv_config : Optional[ConvConfig]
        The partial overriding configuration for conversation template. Will first
        load the predefined template with the name specified in ``conv_template``
        and then override some of the configuraitons specified in ``conv_config``.
    model_category : Optional[str]
        The category of the model's architecture (e.g. ``llama``, ``gpt_neox``, ``rwkv``).
    model_name : Optional[str]
        Name of the model (e.g. ``Llama-2-7b-chat-hf``).
    """

    model_lib: Optional[str] = None
    local_id: Optional[str] = None
    conv_template: Optional[str] = None
    temperature: Optional[float] = None
    repetition_penalty: Optional[float] = None
    top_p: Optional[float] = None
    mean_gen_len: Optional[int] = None
    max_gen_len: Optional[int] = None
    shift_fill_factor: Optional[float] = None
    tokenizer_files: Optional[List[str]] = None
    conv_config: Optional[ConvConfig] = None
    model_category: Optional[str] = None
    model_name: Optional[str] = None


class PlaceInPrompt(Enum):
    """The place of an input message in a prompt."""

    # The input message should have role names and corresponding seperators appended both prior to it and after it,
    # making it a complete prompt.
    All = 0
    # The input message is only the beginning part of a prompt, no role name and separator should be appended after
    # the message since there will be future messages appended after the message.
    Begin = 1
    # The input message is in the middle of a prompt, nothing should be appended before or after the message.
    Middle = 2
    # The input message is the ending part of a prompt, no role name and separator should be appended prior to it
    # since the message is concatenated to some prior messages.
    End = 3


def _get_model_path(model: str) -> (str, str):
    """Use user-provided argument ``model`` to search for a valid model path.

    We define "valid" as having an ``mlc-chat-config.json`` right under the folder.

    Parameters
    ----------
    model : str
        User's input; may be a compiled model's name, or a full path.

    Returns
    ------
    model_path : str
        A "valid" path to model folder, with ``os.isfile(os.path.join(model_path,
        "mlc-chat-config.json"))`` being ``True``.
    chat_file : str
        Essentially ``os.path.join(model_path, "mlc-chat-config.json")``.

    Raises
    ------
    FileNotFoundError: if we cannot find a valid `model_path`.
    """
    # Note that the order of this list corresponds to our search priority
    candidate_paths = [
        f"{model}",  # full path, or just the name
        f"dist/prebuilt/{model}",  # Using prebuilt workflow
        f"dist/{model}/params",  # Default directory after mlc_llm.build_model()
        f"dist/prebuilt/mlc-chat-{model}",  # Also prebuilt workflow, but missed prefix
    ]

    # Look for the first folder that has `mlc-chat-config.json` under it
    for candidate in candidate_paths:
        chat_file = os.path.join(candidate, "mlc-chat-config.json")
        if os.path.isfile(chat_file):
            print(f"Using model folder: {os.path.abspath(candidate)}")
            print(f"Using mlc chat config: {os.path.abspath(chat_file)}")
            return candidate, chat_file

    # Failed to find a valid model_path, analyzing error for user

    # First see if any candidate path is an actual folder
    found_folder = False
    valid_dir_str = ""
    for candidate in candidate_paths:
        if os.path.isdir(candidate):
            valid_dir_str += f"- {os.path.abspath(candidate)}\n"
            found_folder = True

    if found_folder:
        # Error 1: there is a folder, but not an mlc-llm model folder (E1)
        err_msg = (
            "The model folder provided does not seem to refer to a valid mlc-llm model folder.\n"
            "Specifically, we cannot find `mlc-chat-config.json`, a required file. You should "
            "provide a path that contains the file.\n"
            "According to your input `model`, we looked at folder(s):\n"
            f"{valid_dir_str}"
            "MLC-Chat consumes models that are processed by the MLC-LLM build process.\n"
            f"Please checkout {_PYTHON_GET_STARTED_TUTORIAL_URL} for an example on "
            "how to load a model."
        )
        raise FileNotFoundError(err_msg)
    else:
        # Error 2: cannot find a folder (E0)
        all_paths_str = ""
        for path in candidate_paths:
            all_paths_str += f"- {path}\n"
        err_msg = (
            "Cannot find the model folder. We searched over the following possible paths:\n"
            f"{all_paths_str}"
            "You can try to pass in `model=/path/to/your-model-path`, and confirm "
            "that it contains `mlc-chat-config.json`, among other essential files.\n"
            f"Please checkout {_PYTHON_GET_STARTED_TUTORIAL_URL} for an "
            "example on how to load a model."
        )
        raise FileNotFoundError(err_msg)


def _get_chat_config(config_file_path: str, user_chat_config: Optional[ChatConfig]) -> ChatConfig:
    """Read in the config file in model path, then potentially override with user input.

    Parameters
    ----------
    config_file_path : str
        ``chat_file`` returned by ``_get_model_path()``.
    user_chat_config : Optional[ChatConfig]
        User's input, a partial ``ChatConfig`` to override the one in ``config_file_path``.

    Returns
    ------
    final_chat_config : ChatConfig
        ``ChatConfig`` corresponding to ``config_file_path``, overriden by ``user_chat_config``.
    """
    final_chat_config = None
    with open(config_file_path, mode="rt", encoding="utf-8") as f:
        json_object = json.load(f)
        final_chat_config = ChatConfig(**json_object)
    if user_chat_config is not None:
        # We override using user's chat config
        for field in fields(user_chat_config):
            field_name = field.name
            field_value = getattr(user_chat_config, field_name)
            if field_value is not None:
                setattr(final_chat_config, field_name, field_value)
    return final_chat_config


def _get_lib_module(
    model: str,
    model_path: str,
    chat_config: ChatConfig,
    lib_path: Optional[str],
    device_name: str,
    config_file_path: str,
) -> tvm.runtime.Module:
    """Look up the model library. Then return a corresponding ``tvm`` runtime Module.

    Parameters
    ----------
    model : str
        User's input; may be a compiled model's name, or a full path.
    model_path : str
        Model path found by `_get_model_path`.
    chat_config : ChatConfig
        Chat config after potential overrides. Returned by ``_get_chat_config``.
    lib_path : Optional[str]
        User's input. Supposedly a full path to model library. Prioritized to use.
    device_name : str
        User's input. Used to construct the library model file name.
    config_file_path : str
        The path to ``mlc-chat-config.json``. Used for error message making.

    Returns
    ------
    lib_module : tvm.runtime.Module
        A tvm runtime module corresponding to the model library we find.

    Raises
    ------
    FileNotFoundError: if we cannot find a valid model library file.
    """
    # 1. Use user's lib_path if provided
    if lib_path is not None:
        if os.path.isfile(lib_path):
            print(f"Using library model: {lib_path}")
            return tvm.runtime.load_module(lib_path)
        else:
            err_msg = (
                f"The `lib_path` you passed in is not a file: {lib_path}.\nPlease checkout "
                f"{_PYTHON_GET_STARTED_TUTORIAL_URL} for an example on how to load a model."
            )
            raise FileNotFoundError(err_msg)

    # 2. Generate all possible file names according to OS
    candidate_lib_names = []
    if sys.platform.startswith("linux"):
        candidate_lib_names = [f"{chat_config.model_lib}-{device_name}.so"]
    elif sys.platform.startswith("Darwin"):
        # Note that `dylib` comes before `so` since we prioritize `dylib` for MacOS
        candidate_lib_names = [
            f"{chat_config.model_lib}-{device_name}.dylib",
            f"{chat_config.model_lib}-{device_name}.so",
        ]
    elif sys.platform.startswith("win32"):
        candidate_lib_names = [f"{chat_config.model_lib}-{device_name}.dll"]
    else:
        candidate_lib_names = [
            f"{chat_config.model_lib}-{device_name}.dylib",
            f"{chat_config.model_lib}-{device_name}.so",
            f"{chat_config.model_lib}-{device_name}.dll",
        ]

    # 3. Genereate possible model library paths
    candidate_paths = []
    for lib_name in candidate_lib_names:
        # Equivalent to {model_path}/../
        pardir_model_path = os.path.abspath(os.path.join(os.path.abspath(model_path), os.pardir))
        candidate_paths.extend(
            [
                f"{lib_name}",
                f"dist/prebuilt/lib/{lib_name}",  # Using prebuilt workflow
                f"dist/{model}/{lib_name}",  # Default directory after mlc_llm.build_model()
                os.path.join(model_path, lib_name),  # User put library inside `model_path`
                os.path.join(pardir_model_path, lib_name),  # Under parent directory of `model_path`
            ]
        )

    # 4. Search for model library
    for candidate in candidate_paths:
        if os.path.isfile(candidate):
            print(f"Using library model: {os.path.abspath(candidate)}")
            return tvm.runtime.load_module(candidate)

    # 5. Error
    err_msg = (
        f"Cannot find the model library that corresponds to `{chat_config.model_lib}`.\n"
        f"`{chat_config.model_lib}` is either provided in the `chat_config` "
        f"you passed in, or specified in {config_file_path}.\n"
        "We searched over the following possible paths: \n"
    )
    for candidate in candidate_paths:
        err_msg += f"- {candidate}\n"
    err_msg += (
        "If you would like to directly specify the model library path, you may "
        "consider passing in the `lib_path` parameter.\n"
        f"Please checkout {_PYTHON_GET_STARTED_TUTORIAL_URL} for an example "
        "on how to load a model."
    )
    raise FileNotFoundError(err_msg)


def _convert_chat_config_to_json_str(chat_config: Optional[ChatConfig], conv_template: str) -> str:
    """Convert user's input ChatConfig to a json string, omitting ``None`` fields.

    Parameters
    ----------
    chat_config : Optional[ChatConfig]
        User's input. A partial ChatConfig for overriding ``mlc-chat-config.json``.
    conv_template : str
        The ``conv_template`` that will be used after considering potential override.

    Returns
    ------
    json_str : str
        A JSON string that corresponds to user's ``chat_config`` input.
        Returns "" if ``chat_config`` unspecified.
    """
    if chat_config is None:
        return ""
    # Current logic does not allow partial ChatConfig without specifying the
    # conv_template. Hence we use the conv_template after considering potential overrides.
    chat_config.conv_template = conv_template
    # Only want to keep entries that are not None; otherwise, we would override things to None
    assert hasattr(ChatConfig, "conv_config")  # in case dataclass attribute name changes
    chat_dict = {}
    for k, v in asdict(chat_config).items():
        if k == "conv_config" and v is not None:
            # conv template is another dict, do the same thing
            conv_dict = {}
            for conv_k, conv_v in v.items():
                if conv_v is not None:
                    conv_dict[conv_k] = conv_v
            chat_dict[k] = conv_dict
            continue

        if v is not None:
            chat_dict[k] = v

    return json.dumps(chat_dict)


def _detect_local_device(device_id: int = 0):
    """Automatically detect the local device if user does not specify.

    Parameters
    ----------
    device_id : int
        The local device id.

    Returns
    ------
    dev : Device
        The local device.
    """
    if tvm.metal().exist:
        return tvm.metal(device_id), "metal"
    if tvm.rocm().exist:
        return tvm.rocm(device_id), "rocm"
    if tvm.cuda().exist:
        return tvm.cuda(device_id), "cuda"
    if tvm.vulkan().exist:
        return tvm.vulkan(device_id), "vulkan"
    if tvm.opencl().exist:
        return tvm.opencl(device_id), "opencl"

    print(
        "None of the following device is detected: metal, rocm, cuda, vulkan, opencl. Switch to llvm instead."
    )
    return tvm.cpu(device_id), "llvm"


def _first_idx_mismatch(str1, str2):
    """Find the first index that mismatch in two strings. Helper function for generating the output."""
    for i, (char1, char2) in enumerate(zip(str1, str2)):
        if char1 != char2:
            return i
    return min(len(str1), len(str2))


class ChatModule:
    def __init__(
        self,
        model,
        device_name: str = "auto",
        device_id: int = 0,
        chat_config: Optional[ChatConfig] = None,
        lib_path: Optional[str] = None,
    ):
        r"""Initialize a chat module.

        Parameters
        ----------
        model: str
            The model folder after compiling with MLC-LLM build process. The parameter
            can either be the model name with its quantization scheme
            (e.g. ``Llama-2-7b-chat-hf-q4f16_1``), or a full path to the model
            folder. In the former case, we will use the provided name to search
            for the model folder over possible paths.
        device_name : str
            The device name, enter one of "cuda", "metal", "vulkan", "rocm", "opencl", "auto".
            If "auto", the local device will be automatically detected.
        device_id : int
            The device id passed to ``tvm``.
        chat_config : Optional[ChatConfig]
            A ``ChatConfig`` instance partially filled. Will be used to override the
            ``mlc-chat-config.json``.
        lib_path : Optional[str]
            The full path to the model library file to use (e.g. a ``.so`` file).
        """
        # 1. Get self.device
        if device_name == "cuda":
            self.device = tvm.cuda(device_id)
        elif device_name == "metal":
            self.device = tvm.metal(device_id)
        elif device_name == "vulkan":
            self.device = tvm.vulkan(device_id)
        elif device_name == "rocm":
            self.device = tvm.rocm(device_id)
        elif device_name == "opencl":
            self.device = tvm.opencl(device_id)
        elif device_name == "auto":
            self.device, device_name = _detect_local_device(device_id)
            print(f"system automatically detected device: {device_name}")
        else:
            raise ValueError(
                f"invalid device name: {device_name}. Please choose from the following: \
                             cuda, metal, vulkan, rocm, opencl, auto."
            )
        device_type = self.device.device_type

        # 2. Populate chat module and their functions
        fcreate_chat_mod = tvm.get_global_func("mlc.llm_chat_create")
        assert fcreate_chat_mod is not None
        chat_mod = fcreate_chat_mod(device_type, device_id)

        # chat module related functions
        self.reload_func = chat_mod["reload"]
        self.unload_func = chat_mod["unload"]
        self.prefill_func = chat_mod["prefill"]
        self.embed_func = chat_mod["embed"]
        self.prefill_with_embed_func = chat_mod["prefill_with_embed"]
        self.decode_func = chat_mod["decode"]
        self.reset_chat_func = chat_mod["reset_chat"]
        self.load_json_override_func = chat_mod["load_json_override"]
        self.stopped_func = chat_mod["stopped"]
        self.get_message_func = chat_mod["get_message"]
        self.runtime_stats_text_func = chat_mod["runtime_stats_text"]
        self.reset_runtime_stats_func = chat_mod["reset_runtime_stats"]
        self.get_config_json_func = chat_mod["get_config_json"]
        self.process_system_prompts_func = chat_mod["process_system_prompts"]
        self.evaluate_func = chat_mod["evaluate"]
        self.get_role0_func = chat_mod["get_role0"]
        self.get_role1_func = chat_mod["get_role1"]

        # 3. Look up model_path
        self.model_path, self.config_file_path = _get_model_path(model)

        # 4. Instantiate chat_config
        self.chat_config = _get_chat_config(self.config_file_path, chat_config)

        # 5. Look up model library
        self.lib_path = _get_lib_module(
            model, self.model_path, self.chat_config, lib_path, device_name, self.config_file_path
        )

        # 6. Call reload
        user_chat_config_json_str = _convert_chat_config_to_json_str(
            chat_config, self.chat_config.conv_template
        )
        self._reload(self.lib_path, self.model_path, user_chat_config_json_str)

    def generate(self, prompt: str, progress_callback=callback.stream_to_stdout(interval=2)):
        r"""A high-level method that generates the response from the chat module given a user prompt.
        User can specify which callback method to use upon receiving the response.

        Parameters
        ----------
        prompt : str
            The user input prompt, i.e. a question to ask the chat module.
        progress_callback: object
            Optional argument. The callback method used upon receiving the response from the chat module.
            User should pass in a callback class. See `mlc_chat/callback.py` for a full list
            of available callback classes. By default, the response is streamed to stdout.

        Note
        ----
        The generate api gives the raw response, and no chat bot role name will be displayed
        prior to the response. User can retrieve the role name via :func:`_get_role_1`.
        """
        self._prefill(prompt)
        i, cur_utf8_chars = 0, "".encode("utf-8")
        while not self._stopped():
            self._decode()
            if i % progress_callback.interval == 0 or self._stopped():
                new_msg = self._get_message()
                new_utf8_chars = new_msg.encode("utf-8")
                pos = _first_idx_mismatch(cur_utf8_chars, new_utf8_chars)
                print_msg = ""
                for _ in range(pos, len(cur_utf8_chars)):
                    print_msg += "\b \b"
                for j in range(pos, len(new_utf8_chars)):
                    print_msg += chr(new_utf8_chars[j])
                cur_utf8_chars = new_utf8_chars
                progress_callback(message=print_msg)
            i += 1
        progress_callback(stopped=True)

    def reset_chat(self, chat_config: Optional[ChatConfig] = None):
        r"""Reset the chat session, clear all chat history, and potentially
        override the original `mlc-chat-config.json`.

        Parameters
        ----------
        chat_config : Optional[ChatConfig]
            A ``ChatConfig`` instance partially filled. If specified, the chat
            module will reload the `mlc-chat-config.json`, and override it with
            ``chat_config``, just like in initialization.

        Note
        ----
        The model remains the same after :func:`reset_chat`.
        To reload module, please either re-initialize a :class:`ChatModule` instance
        or use :func:`_reload` instead.
        """
        self.reset_chat_func()
        if chat_config is not None:
            # Redo the overriding
            self.chat_config = _get_chat_config(self.config_file_path, chat_config)
            user_chat_config_json_str = _convert_chat_config_to_json_str(
                chat_config, self.chat_config.conv_template
            )
            # Second argument is `partial_update = True`
            self.load_json_override_func(user_chat_config_json_str, True)

    def embed_text(self, input: str, place_in_prompt: PlaceInPrompt = PlaceInPrompt.Middle):
        r"""Given a text input, get the embedding of the tokenized prompt.
        User can decide where to place the input in the prompt. By default, no prompts will be
        padded before or after the input text.

        Parameters
        ----------
        input : str
            The user input string.
        place_in_prompt: PlaceInPrompt
            The place of the input message in the prompt. See `class PlaceInPrompt` for details.
        """
        return self.embed_func(input, place_in_prompt.value)

    def runtime_stats_text(self) -> str:
        r"""Get the runtime stats of the encoding step, decoding step, (and embedding step if exists)
        of the chat module in text form.

        Returns
        -------
        stats : str
            The runtime stats text.
        """
        return self.runtime_stats_text_func()

    def _reload(self, lib: str, model_path: str, app_config_json: str = ""):
        r"""Reload the chat module from the given library and model path.

        Parameters
        ----------
        lib : str
            The library path.
        model_path : str
            The model path.
        app_config_json: str
            The partial config that is used to partially override the model configuration.
        """
        self.reload_func(lib, model_path, app_config_json)

    def _unload(self):
        r"""Unload the chat module and clear memory of all loaded models."""
        self.unload_func()

    def _prefill(
        self,
        input: str,
        decode_next_token: bool = True,
        place_in_prompt: PlaceInPrompt = PlaceInPrompt.All,
    ):
        r"""Run prefill stage for a given input and optionally decode the first output token.
        User can decide where to place the input in the prompt.

        Parameters
        ----------
        input : str
            The user input string.
        decode_next_token : bool
            Whether to decode the next token after prefilling.
        place_in_prompt: PlaceInPrompt
            The place of the input message in the prompt. See `class PlaceInPrompt` for details.
        """
        self.prefill_func(input, decode_next_token, place_in_prompt.value)

    def _prefill_with_embed(self, embedding: tvm.runtime.NDArray, decode_next_token: bool = True):
        r"""Given an embedding, run the prefill stage and optionally decode the first output token.

        Parameters
        ----------
        embedding : tvm.runtime.NDArray
            The embedding of user input.
        decode_next_token : bool
            Whether to decode the next token after prefilling.
        """
        self.prefill_with_embed_func(embedding, decode_next_token)

    def _decode(self):
        r"""Decode the next token, the decoding result is stored in a buffer and
        can be retrieved by :func:`get_message`.
        """
        self.decode_func()

    def _stopped(self) -> bool:
        r"""Check if the stop condition is met for the current round.

        Returns
        -------
        stopped : bool
        """
        return self.stopped_func() != 0

    def _get_message(self) -> str:
        r"""Get the output message in the current round.

        Returns
        -------
        message : str

        Note
        ----
        This function returns the message that corresponds to
        all the tokens decoded so far.
        """
        return self.get_message_func()

    def _get_config_json(self):
        r"""Get the configuration of the chat module in a single json string.

        Returns
        -------
        config : str
            The config json string.
        """
        return self.get_config_json_func()

    def _load_json_override(self, config_str: str, partial_update: bool = False):
        r"""Load JSON config and override existing configurations for the chat module.

        Parameters
        ----------
        config_str : str
            A json config string that partially specifies some of the options.
        partial_update : bool
            Whether it's a partial update or full update, if set to true, we perform a partial update
            on some of the provided options; if set to false, all options must be provided.
        """
        self.load_json_override_func(config_str, partial_update)

    def _get_role_0(self):
        r"""Get the name of role 0 in the conversation.

        Returns
        -------
        name : str
            The name of role 0.
        """
        return self.get_role0_func()

    def _get_role_1(self):
        r"""Get the name of role 1 in the conversation.

        Returns
        -------
        name : str
            The name of role 1.
        """
        return self.get_role1_func()

    def _reset_runtime_stats(self):
        r"""Reset the runtime stats, clear all performance history."""
        self.reset_runtime_stats_func()

    def _process_system_prompts(self):
        r"""Pre-process by prefilling the system prompts, running prior to any user input."""
        self.process_system_prompts_func()

    def _evaluate(self, token_len: int, generate_len: int):
        r"""Perform a quick evaluation of the chat pipeline with toy inputs.
        Use for debug purpose only."""
        self.evaluate_func(token_len, generate_len)
