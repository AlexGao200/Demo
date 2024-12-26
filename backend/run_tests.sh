#!/bin/bash

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
CYAN='\033[1;36m'
NC='\033[0m'

# Default to watch mode
WATCH_MODE=true

# Function to copy environment files
setup_env_files() {
    # Copy environment files to backend directory for docker build context
    if [ -f "../.env" ]; then
        cp "../.env" ".env"
        echo -e "${GREEN}Copied .env file for testing${NC}"
    else
        echo -e "${RED}Warning: .env file not found${NC}"
        return 1
    fi

    if [ -f "../.env.test" ]; then
        cp "../.env.test" ".env.test"
        echo -e "${GREEN}Copied .env.test file for testing${NC}"
    else
        echo -e "${RED}Warning: .env.test file not found${NC}"
        return 1
    fi
}

# Function to cleanup environment files
cleanup_env_files() {
    # Remove copied environment files
    rm -f ".env" ".env.test"
}

# Function to cleanup everything
cleanup() {
    cleanup_env_files
    cleanup_watch_mode
}

# Ensure cleanup happens on script exit
trap cleanup EXIT

validate_test_path() {
    local test_path=$1

    # If no test path specified, it's valid (run all tests)
    if [ -z "$test_path" ]; then
        return 0
    fi

    # Convert potential relative path to absolute
    local full_path
    if [[ "$test_path" = /* ]]; then
        full_path="$test_path"
    else
        full_path="$(pwd)/$test_path"
    fi

    # Strip any pytest filtering (e.g., ::test_function_name)
    local base_path="${full_path%%::*}"

    # Check if path exists
    if [ ! -e "$base_path" ]; then
        echo -e "${RED}Error: Test path does not exist: $base_path${NC}"
        return 1
    fi

    # If it's a directory, check if it contains any test files
    if [ -d "$base_path" ]; then
        if ! find "$base_path" -name "test_*.py" -print -quit | grep -q .; then
            echo -e "${RED}Error: No test files found in directory: $base_path${NC}"
            return 1
        fi
    # If it's a file, check if it's a python file and starts with test_
    elif [ -f "$base_path" ]; then
        if [[ ! "$base_path" =~ \.py$ ]] || [[ ! $(basename "$base_path") =~ ^test_ ]]; then
            echo -e "${RED}Error: Not a valid test file: $base_path${NC}"
            return 1
        fi
    fi

    return 0
}

# Function to get the actual container name
get_container_name() {
    docker-compose -f ../docker-compose.test.yml ps -q backend | xargs docker inspect -f '{{.Name}}' | sed 's/\///'
}

# Function to check if backend is still building
is_backend_building() {
    local container_id=$(docker-compose -f ../docker-compose.test.yml ps -q backend)
    if [ -n "$container_id" ]; then
        local state=$(docker inspect -f '{{.State.Status}}' "$container_id" 2>/dev/null)
        local health=$(docker inspect -f '{{.State.Health.Status}}' "$container_id" 2>/dev/null)
        if [ "$state" = "created" ] || [ "$state" = "starting" ] || [ "$health" = "starting" ]; then
            return 0  # true, still building
        fi
    fi
    return 1  # false, not building
}

# Function to check service health
check_service() {
    local service=$1
    local check_command=$2
    local max_retries=${3:-30}
    local retry_interval=${4:-2}

    echo "Checking $service..."

    # If checking MongoDB, first wait for backend to finish building
    if [ "$service" = "MongoDB" ]; then
        while is_backend_building; do
            echo -e "\r${YELLOW}Waiting for backend container to finish building...${NC}"
            sleep $retry_interval
        done
    fi

    # Now check the actual service
    for i in $(seq 1 $max_retries); do
        if eval "$check_command" > /dev/null 2>&1; then
            echo -e "${GREEN}$service is ready${NC}"
            return 0
        fi
        echo -n "."
        if [ $i -eq $max_retries ]; then
            echo -e "\n${RED}$service failed to start${NC}"
            return 1
        fi
        sleep $retry_interval
    done
}

translate_path() {
    local original_dir="$1"
    local test_path="$2"
    local project_root="$(git rev-parse --show-toplevel 2>/dev/null || echo "$HOME/path/to/your/project")"

    if [[ "$test_path" = /* ]]; then
        absolute_path="$test_path"
    else
        absolute_path="$original_dir/$test_path"
    fi

    if [ -e "$absolute_path" ]; then
        relative_path=${absolute_path#$project_root/}
        relative_path=${relative_path#backend/}
        relative_path=${relative_path#tests/}
        echo "tests/$relative_path"
    else
        echo "$test_path"
    fi
}

SCREEN_NAME="pytest_watch"

# Function to start watch mode in a new terminal
start_watch_mode() {
    # Kill any existing screen session with the same name
    screen -X -S "$SCREEN_NAME" quit > /dev/null 2>&1

    # Copy environment files before starting containers
    setup_env_files

    # Start a new screen session for watch mode with error handling
    screen -dmS "$SCREEN_NAME" bash -c "cd $(pwd)/.. && (docker compose -f docker-compose.test.yml up --watch --build || (echo -e '${RED}Docker setup failed. Press Enter to exit...${NC}' && read -r))"

    echo -e "${YELLOW}Started watch mode in background - files will sync automatically${NC}"
    echo -e "${YELLOW}Use 'screen -r $SCREEN_NAME' to view watch process if needed${NC}"

    # Give services time to start
    sleep 5
}

# Function to cleanup watch mode
cleanup_watch_mode() {
    if screen -list | grep -q "$SCREEN_NAME"; then
        # Gracefully stop docker compose
        screen -S "$SCREEN_NAME" -X stuff "^C"
        sleep 2
        screen -X -S "$SCREEN_NAME" quit
    fi
    docker-compose -f ../docker-compose.test.yml down
}

# Ensure cleanup happens on script exit, but not for setup failures
trap cleanup_watch_mode EXIT

# Function to get number of CPU cores (cross-platform)
get_cpu_count() {
    if [[ "$(uname)" == "Darwin" ]]; then
        sysctl -n hw.ncpu
    elif [[ "$(uname)" == "Linux" ]]; then
        nproc
    else
        echo 4  # Default fallback
    fi
}

# Function to merge pytest arguments, with user args taking precedence
merge_pytest_args() {
    local default_args_str="$1"
    local user_args_str="$2"

    # Convert space-separated strings to arrays
    read -ra default_args <<< "$default_args_str"
    read -ra user_args <<< "$user_args_str"

    local merged_args=()
    local used_flags=()
    local skip_next=false

    # Helper function to get base flag
    get_base_flag() {
        echo "$1" | sed -E 's/=.*$//' | sed -E 's/[[:space:]]+.*$//'
    }

    # Helper function to check if flag is already used
    is_flag_used() {
        local flag=$1
        local base_flag=$(get_base_flag "$flag")

        for used_flag in "${used_flags[@]}"; do
            if [[ "$used_flag" == "$base_flag" ]] || \
               [[ "$base_flag" == "-v" && "$used_flag" == "--verbose" ]] || \
               [[ "$base_flag" == "--verbose" && "$used_flag" == "-v" ]] || \
               [[ "$base_flag" == "-s" && "$used_flag" == "--no-capture" ]] || \
               [[ "$base_flag" == "--no-capture" && "$used_flag" == "-s" ]] || \
               [[ "$base_flag" == "-l" && "$used_flag" == "--showlocals" ]] || \
               [[ "$base_flag" == "--showlocals" && "$used_flag" == "-l" ]]; then
                return 0
            fi
        done
        return 1
    }

    # First, add all user arguments
    for ((i=0; i<${#user_args[@]}; i++)); do
        if ! $skip_next; then
            arg="${user_args[i]}"
            if [[ "$arg" == -* ]]; then
                base_flag=$(get_base_flag "$arg")
                merged_args+=("$arg")
                used_flags+=("$base_flag")

                # Check if next argument is a value
                if [[ "$arg" != *"="* ]] && [[ " -k --maxfail --tb " =~ " $base_flag " ]] && \
                   [ $((i + 1)) -lt ${#user_args[@]} ]; then
                    skip_next=true
                    merged_args+=("${user_args[i+1]}")
                fi
            else
                merged_args+=("$arg")
            fi
        else
            skip_next=false
        fi
    done

    # Then add default arguments that haven't been overridden
    for ((i=0; i<${#default_args[@]}; i++)); do
        if ! $skip_next; then
            arg="${default_args[i]}"
            if [[ "$arg" == -* ]]; then
                if ! is_flag_used "$arg"; then
                    base_flag=$(get_base_flag "$arg")
                    merged_args+=("$arg")
                    used_flags+=("$base_flag")

                    # Check if next argument is a value
                    if [[ "$arg" != *"="* ]] && [[ " -k --maxfail --tb " =~ " $base_flag " ]] && \
                       [ $((i + 1)) -lt ${#default_args[@]} ]; then
                        skip_next=true
                        merged_args+=("${default_args[i+1]}")
                    fi
                fi
            elif ! is_flag_used "$arg"; then
                merged_args+=("$arg")
            fi
        else
            skip_next=false
        fi
    done

    # Convert array back to space-separated string
    echo "${merged_args[*]}"
}

# Function to run tests
run_tests() {
    local test_pattern=$1
    shift  # Remove test_pattern from args
    local pytest_args=("$@")  # Remaining arguments are pytest args

    echo -e "${GREEN}Running tests: ${test_pattern:-all tests}${NC}"

    # Verify we're in the backend directory
    if [ ! -d "tests" ]; then
        echo -e "${RED}Error: 'tests' directory not found. Please run this script from the backend directory.${NC}"
        exit 1
    fi

    # Validate test path before starting containers
    if ! validate_test_path "$test_pattern"; then
        return 1
    fi

    # Only start containers if they're not already running
    if ! docker-compose -f ../docker-compose.test.yml ps | grep -q "backend.*Up"; then
        # Stop any running containers
        echo "Stopping any existing test containers..."
        docker-compose -f ../docker-compose.test.yml down

        # Copy environment files before starting containers
        if ! setup_env_files; then
            echo -e "${RED}Failed to setup environment files${NC}"
            return 1
        fi

        # Start test environment
        echo "Starting test environment..."
        if [ "$WATCH_MODE" = true ]; then
            start_watch_mode
        else
            if ! docker-compose -f ../docker-compose.test.yml up -d --build; then
                echo -e "${RED}Failed to start test environment${NC}"
                echo -e "${YELLOW}Press Enter to exit...${NC}"
                read -r
                exit 1
            fi
        fi

        # Check MongoDB
        if ! check_service "MongoDB" "docker-compose -f ../docker-compose.test.yml exec -T mongo mongosh --eval 'db.runCommand({ ping: 1 })'"; then
            docker-compose -f ../docker-compose.test.yml logs mongo
            echo -e "${YELLOW}Press Enter to exit...${NC}"
            read -r
            exit 1
        fi

        # Check Elasticsearch
        if ! check_service "Elasticsearch" "curl -s 'http://localhost:9201'"; then
            docker-compose -f ../docker-compose.test.yml logs elasticsearch
            echo -e "${YELLOW}Press Enter to exit...${NC}"
            read -r
            exit 1
        fi
    fi

    # Get the actual container name
    CONTAINER_NAME=$(get_container_name)
    if [ -z "$CONTAINER_NAME" ]; then
        echo -e "${RED}Failed to get backend container name${NC}"
        docker-compose -f ../docker-compose.test.yml logs backend
        echo -e "${YELLOW}Press Enter to exit...${NC}"
        read -r
        exit 1
    fi

    # Determine number of CPU cores for parallel testing
    if [ -z "$PYTEST_WORKERS" ]; then
        PYTEST_WORKERS=$(( $(get_cpu_count) - 1 ))
        if [ "$PYTEST_WORKERS" -lt 2 ]; then
            PYTEST_WORKERS=2
        fi
    fi

    # Prepare default pytest arguments
    # Removed -s flag and added --tb=short for cleaner output
    default_args="-v --color=yes -n $PYTEST_WORKERS --setup-show"

    # Add any additional pytest options from environment
    if [ ! -z "$PYTEST_ADDOPTS" ]; then
        default_args="$default_args $PYTEST_ADDOPTS"
    fi

    # Convert pytest_args array to space-separated string
    user_args="${pytest_args[*]}"

    # Merge arguments, with user args taking precedence
    PYTEST_ARGS=$(merge_pytest_args "$default_args" "$user_args")

    echo -e "${GREEN}Running tests with $PYTEST_WORKERS workers${NC}"
    echo -e "${YELLOW}Pytest arguments: $PYTEST_ARGS${NC}"

    # Clear terminal before running tests
    printf '\033c' && clear

    # Run pytest with proper signal handling and output capturing
    if [ -z "$test_pattern" ]; then
        docker exec -e PYTHONUNBUFFERED=1 -e RUST_BACKTRACE=1 "$CONTAINER_NAME" pytest $PYTEST_ARGS tests/
    else
        docker exec -e PYTHONUNBUFFERED=1 -e RUST_BACKTRACE=1 "$CONTAINER_NAME" pytest $PYTEST_ARGS "$test_pattern"
    fi

    return $?
}

# Interactive test runner
run_interactive_tests() {
    local test_pattern="$1"
    shift
    local pytest_args=("$@")
    local history_file="/tmp/pytest_history"
    touch "$history_file"

    # Enable command history
    export HISTFILE="$history_file"
    export HISTSIZE=1000
    export HISTFILESIZE=2000
    set -o history

    # Add initial test pattern to history if provided
    if [ -n "$test_pattern" ]; then
        history -s "$test_pattern"
        history -w "$history_file"
    fi

    while true; do
        # If we have an initial test pattern, run it and skip prompt
        if [ -n "$test_pattern" ]; then
            run_tests "$test_pattern" "${pytest_args[@]}"
            test_pattern=""
            pytest_args=()
            continue  # Skip the prompt and go to next iteration
        fi

        echo -e "\n${YELLOW}Enter test pattern:${NC}"
        echo "  - Press Enter to run all tests"
        echo "  - Use up/down arrows for history"
        echo "  - Type 'q' to quit"
        echo "  - Type 'd' for debug shell"
        echo "  - Type 'l' for container logs"
        echo "  - Type 'w' to view watch process"
        echo "Ex: tests/unit/services/test_auth_service_unit.py::TestLoginFlow::test_verify_token_success"
        echo -en "🐐 aca-test>${NC} "  # Custom prompt for test environment
        read -e input_pattern
        history -s "$input_pattern"

        case "$input_pattern" in
            q|quit|exit)
                echo -e "${YELLOW}Shutting down test environment...${NC}"
                cleanup_watch_mode
                exit 0
                ;;
            d|debug)
                echo -e "${YELLOW}Starting debug shell...${NC}"
                docker exec -it "$(get_container_name)" bash
                continue
                ;;
            l|logs)
                echo -e "${YELLOW}Container logs:${NC}"
                docker logs "$(get_container_name)"
                continue
                ;;
            w|watch)
                if [ "$WATCH_MODE" = true ]; then
                    echo -e "${YELLOW}Attaching to watch process (Ctrl-a d to detach)...${NC}"
                    screen -r "$SCREEN_NAME"
                else
                    echo -e "${RED}Watch mode is not enabled${NC}"
                fi
                continue
                ;;
            "")
                run_tests "" "${pytest_args[@]}"  # Run all tests
                ;;
            *)
                run_tests "$input_pattern" "${pytest_args[@]}"  # Run specific tests
                ;;
        esac

        local exit_code=$?
        if [ $exit_code -ne 0 ]; then
            echo -e "${RED}Tests failed.${NC}"
            echo -e "${YELLOW}Options:${NC}"
            echo "1. Enter new test pattern"
            echo "2. Type 'd' for debug shell"
            echo "3. Type 'l' for container logs"
            echo "4. Type 'w' to view watch process"
            echo "5. Type 'q' to quit"
        fi
    done
}

# Show usage if --help flag is used
if [ "$1" = "--help" ]; then
    cat << EOF
Usage: $0 [options] [test_pattern] [pytest_args...]

Interactive test runner with history support and pytest argument passing.
Watch mode is enabled by default - files will sync automatically but tests run only when requested.

Options:
  --no-watch                  Disable watch mode (default: watch mode enabled)
  --from-dir <dir>           Specify original directory for test path translation
  --help                     Show this help message

Examples:
  $0                                              # Start with watch mode (default)
  $0 --no-watch                                  # Run without watch mode
  $0 tests/unit                                  # Run unit tests with watch mode
  $0 tests/integration                          # Run integration tests with watch mode
  $0 tests/integration/test_auth_routes.py      # Run specific test file
  $0 tests/integration/test_auth_routes.py::test_login  # Run specific test
  $0 tests/unit -vv                             # Run unit tests with increased verbosity
  $0 tests/integration --tb=short               # Run integration tests with short traceback
  $0 tests/unit --pdb -vv                       # Run with debugger and very verbose output

Pytest Arguments:
  -v, --verbose                 # Increase verbosity
  -vv                          # Increase verbosity more
  -s                           # Don't capture stdout (use when debugging)
  --pdb                        # Drop into debugger on failures
  --tb=auto|long|short|native  # Traceback print mode
  -x, --exitfirst             # Exit on first failure
  --maxfail=n                 # Exit after n failures
  -l, --showlocals            # Show local variables in tracebacks

Commands in interactive mode:
  - Enter test pattern     # Run specific tests
  - Press Enter           # Run all tests
  - Up/Down arrows        # Navigate test history
  - d or debug           # Start debug shell
  - l or logs            # Show container logs
  - q or quit            # Exit and cleanup

Environment Variables:
  PYTEST_ADDOPTS      # Additional pytest options
  PYTEST_WORKERS=N    # Override automatic worker count (default: CPU cores - 1)
EOF
    exit 0
fi

# Process arguments
original_dir=""
pytest_args=()

while [[ $# -gt 0 ]]; do
    case $1 in
        --no-watch)
            WATCH_MODE=false
            shift
            ;;
        --from-dir)
            original_dir="$2"
            shift 2
            ;;
        --help)
            show_help
            exit 0
            ;;
        -*)
            # Collect pytest arguments
            pytest_args+=("$1")
            shift
            ;;
        *)
            if [ -n "$original_dir" ] && [ -n "$1" ] && [[ "$1" != -* ]]; then
                test_pattern=$(translate_path "$original_dir" "$1")
                shift
            else
                test_pattern="$1"
                shift
            fi
            ;;
    esac
done

# Start interactive test runner
run_interactive_tests "$test_pattern" "${pytest_args[@]}"
